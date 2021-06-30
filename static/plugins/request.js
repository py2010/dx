
// axios请求,简易封装
// exia@qq.com
// 2019-12-24

function dateFormat(date, fmt) {
  if (null == date || undefined == date) return '';
  var o = {
    "M+": date.getMonth() + 1, //月份
    "d+": date.getDate(), //日
    "h+": date.getHours(), //小时
    "m+": date.getMinutes(), //分
    "s+": date.getSeconds(), //秒
    "S": date.getMilliseconds() //毫秒
  };
  if (/(y+)/.test(fmt)) fmt = fmt.replace(RegExp.$1, (date.getFullYear() + "").substr(4 - RegExp.$1.length));
  for (var k in o)
    if (new RegExp("(" + k + ")").test(fmt)) fmt = fmt.replace(RegExp.$1, (RegExp.$1.length == 1) ? (o[k]) : (("00" + o[k]).substr(("" + o[k]).length)));
  return fmt;
}

Date.prototype.toJSON = function () {
  // 重写js函数,设置转json后的时间格式
  return dateFormat(this, 'yyyy-MM-dd hh:mm:ss')
}


function getCookie(name) {
    var prefix = name + "="
    var start = document.cookie.indexOf(prefix)
 
    if (start == -1) {
        return null;
    }
 
    var end = document.cookie.indexOf(";", start + prefix.length)
    if (end == -1) {
        end = document.cookie.length;
    }
 
    var value = document.cookie.substring(start + prefix.length, end)
    return unescape(value);
}

function Requst(v,url,params,method,data,headers) {
    // application/x-www-form-urlencoded
    // console.log(data);
    headers= headers || {'Content-Type':'application/json'};
    getCookie("csrftoken")
    csrftoken = getCookie('csrftoken');
    if (csrftoken) {
        headers['X-Csrftoken']=csrftoken;
    }

    // console.log(headers);
    let result = axios({
        method: method,
        url: url,
        headers:headers,
        params:params,
        data: data,
        // transformRequest:[function(data){
        //     let ret = '';
        //     for(let i in data){
        //         ret += encodeURIComponent(i)+'='+encodeURIComponent(data[i])+"&";
        //     }
        //     console.log(ret);
        //     return ret;
        // }],

    }).then(resp=> {
        return resp.data;
    }).catch(error=>{

        var message = ''
        console.log("=====>",error.response.status)
        switch (error.response.status) {
          case 401:
            message = '请先登录!';
            setTimeout(()=>{top.location.href="/checkaccount/";},3000)
            break
          case 403:
            message = '无权限!'
            break
          case 400:
            if (error.response.config.url.indexOf('/login') >= 0) {
              message = '用户名密码错误!'
            } else {
              for(var key in error.response.data){//遍历json对象的每个key/value对,p为key
                console.log(error.response.data);
                message+=key+": "+JSON.stringify(error.response.data[key])+"<br/>";
              }
            }
            break
          case 404:
            message = '页面不存在!'
            break
          case 500:
            var errmsg=""
            if(error.response.hasOwnProperty("detail")){
              errmsg=error.response.hasOwnProperty("detail")
            }
            message = '服务异常:'+errmsg
            break
          case 502:
            var errmsg=""
            if(error.response.hasOwnProperty("detail")){
              errmsg=error.response.hasOwnProperty("detail")
            }
            message = '服务异常:'+errmsg
            break
          default:
            message = '请求出错!'
          }

        // v.$message.error('api接口请求出错: '+error);
        v.$message({
          showClose: true,
          type: 'error',
          message: message,
          duration: 9000,
          dangerouslyUseHTMLString:true
        })
        // console.log(error);
        return Promise.reject(error);
    });

    return result;
}

function SaveModelForm(v,form_data,header) {
    // 保存ModelForm数据
    console.log(form_data);
    let id;
    let method;
    if(form_data.id){
        // 修改
        method="put";
        id=form_data.id+"/";
    }else{
        // 新增
        method="post";
        id="";
    }
    let obj_url=v.api_url+id;
    return Requst(v,obj_url,{},method,form_data,header)
}

function DelModelForm(v,id,header) {
    let obj_url=v.api_url+id+"/";
    return Requst(v,obj_url,{},'delete',null,header);
}
