# from django.dispatch import receiver
# from django.db.models.signals import post_save, m2m_changed

# from .models import NetPort


# @receiver(post_save, sender=NetPort, dispatch_uid="NetPort_post_save")
# def netport_model_handler(sender, **kwargs):
#     '''model.save()'''
#     obj = kwargs['instance']
#     print('保存model: {}'.format(obj.__dict__))
#     import ipdb;ipdb.set_trace()


# @receiver(m2m_changed, sender=User.addresses.through, dispatch_uid="User_m2m_Address")
# def address_changed(sender, **kwargs):
#     # import ipdb;ipdb.set_trace()
#     address_ids = kwargs.get('pk_set', set())
#     if address_ids and kwargs.get('action') == 'post_add':
#         # print('m2m有添加!!!!!!!!!!', kwargs)
#         # 添加User - Address m2m关联记录, 有设置默认地址,将用户之前的默认地址改为非默认
#         Address.set_default(address_ids)
