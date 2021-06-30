# coding=utf-8

from django.http import JsonResponse
from django.views.generic import View, ListView, DetailView
from django.db.models import Q


class MyDeleteView(View):
    '''批量删除model表数据'''
    model = None

    def post(self, request, *args, **kwargs):
        error = ''
        if self.model:
            ids = request.POST.getlist('id', [])
            if ids:
                try:
                    self.model.objects.filter(id__in=ids).delete()
                except Exception as e:
                    error = str(e)
            else:
                error = '未提供删除对象id, 操作忽略'
        else:
            error = 'View未配置model, 操作忽略'

        return JsonResponse({
            'status': False if error else True,
            'error': error
        })


# class MyPermissionRequiredMixin(PermissionRequiredMixin):
#     '''
#     django的PermissionRequiredMixin不按request.method请求类型进行区分权限,
#     GET/POST/DELETE之前都是先dispatch判断权限, 所以重写使支持Restful方式的权限
#     '''

#     def get_permission_required(self):
#         method = self.request.method  # 根据method返回相应权限


class MyListView(ListView):
    '''带搜索过滤功能的ListView, filter_fields为模糊搜索的字段'''
    template_name = 'generic/_list.html'
    list_fields = []  # 列表页显示的字段
    filter_fields = []  # 是否使用模糊搜索多字段功能
    filter_orm = False  # 是否开启ORM过滤功能
    paginate_by = 30  # 每页条数
    # paginate_orphans = 5  # 尾页少于数量则合并到前一页

    def get_queryset(self):
        qs = self.get_queryset_orm(True) if self.filter_orm else None
        return self.get_queryset_search(qs)

    def get_queryset_search(self, queryset=None):
        # 模糊查询多字段, 各字段逻辑或
        if queryset is None:
            queryset = super().get_queryset()
        s = self.request.GET.get('s')
        if s and self.filter_fields:
            Q_kwargs = {f'{field}__contains': s.strip() for field in self.filter_fields}
            queryset = queryset.filter(Q(_connector='OR', **Q_kwargs))
        return queryset

    def get_queryset_orm(self, ignore_error=False):
        '''
        使ListView支持GET参数ORM查询过滤，
        参数ignore_error, 当ORM字段参数错误时, 是否忽略, 不忽略则查询为空.
        本函数不考虑ORM外键过滤/攻击限制之类的需求，如有请根据model实例自定义。

        如果有其它类型的搜索过滤，则为逻辑与叠加操作过滤。

        示例：
        class xxxListView(xxx):
            xxxx
            get_queryset = get_queryset_orm
            或
            def get_queryset(self):return get_queryset_orm(self, True)

        http://xxx列表页/?orm_city__name=深圳&orm_field__icontains=xx
        相当于queryset.filter(city__name='深圳', field__icontains='xx')
        多个参数一律视为"和"，不支持“或”操作，因为URL的&只是间隔符，不含逻辑与或信息
        '''
        queryset = super().get_queryset()
        for k, v in self.request.GET.items():
            if k.startswith('orm_'):
                # print('ORM_参数', k, v)
                try:
                    queryset = queryset.filter(**{k[4:]: v})
                except Exception:
                    if ignore_error:
                        # 忽略错误的orm表达式参数
                        continue
                    return queryset.none()

        return queryset


class MyDetailView(DetailView):
    template_name = "generic/_detail.html"

    def get_context_data(self, **kwargs):
        """生成各字段key/val，以便在模板中直接使用"""
        context = super().get_context_data(**kwargs)
        self.object.fields_list = []
        for field in self.object._meta.fields:

            if field.choices:
                val = dict(field.flatchoices).get(
                    field.value_from_object(self.object),
                    field.value_from_object(self.object)
                )
            else:
                val = field.value_from_object(self.object)

            self.object.fields_list.append((field.verbose_name or field.attname, val))
        return context


'''
# 使用示例:

class XxxView(LoginRequiredMixin, PermissionRequiredMixin):
    model = models.Xxx
    model_meta = model._meta  # 由于模板中禁止访问"_"开头的属性.


class XxxList(XxxView, ListView):
    # template_name = 'generic/_list.html'
    # permission_required = 'xxx_app_label:view_xxx'
    paginate_by = 20  # 每页条数


class XxxDetail(XxxView, views.MyDetailView):
    permission_required = 'xxx_app_label:view_xxx'


class XxxForm(XxxView):
    template_name = "generic/_form.html"
    fields = '__all__'
    # form_class = forms.XxxForm
    success_url = reverse_lazy('xxx_app_label:xxx_list')


class XxxAdd(XxxForm, CreateView):
    # template_name_suffix = '_add'
    permission_required = 'xxx_app_label:add_xxx'


class XxxUpdate(XxxForm, UpdateView):
    permission_required = 'xxx_app_label:change_xxx'


class XxxDelete(XxxView, views.MyDeleteView):
    permission_required = 'xxx_app_label:delete_xxx'


# URL配置示例

from django.conf.urls import url
from xxx_app_label import views

urlpatterns = [

    url(r'^xxx/add/$', views.XxxAdd.as_view(), name='xxx_add'),
    url(r'^xxx/(?P<pk>\d+)/update/$', views.XxxUpdate.as_view(), name='xxx_update'),
    url(r'^xxx/delete/$', views.XxxDelete.as_view(), name='xxx_delete'),
    url(r'^xxx/(?P<pk>\d+)/$', views.XxxDetail.as_view(), name='xxx_detail'),
    url(r'^xxx/$', views.XxxList.as_view(), name='xxx_list'),

]


'''
