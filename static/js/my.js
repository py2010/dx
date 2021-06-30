

function DeleteObj(that, id, url) {

    if (! url) {
        url = window.location.pathname.replace(/(\/$)/g,'') + '/delete/';
    }
    console.log(that);

    swal({
        title: '确定删除此条数据？',
        // text: "",
        type: "warning",
        showCancelButton: true,
        cancelButtonText: '取消',
        confirmButtonText: '确定',
        confirmButtonColor: "#ed5565",

    })
    .then((result) => {
        if (result.value) {

            var data;
            if (id) {
                data = 'id=' + id
            } else if (that.text=='删除') {
                data = 'id=' + that.parentNode.parentNode.id || that.parentNode.id;
            } else if (that.text=='批量删除') {
                data = $('#list_thatect_form').serialize();
            } else {
                swal('出错', '未知的操作类型: "'+that.text+'"', "error");
                return false;
            }

            // console.log(data);
            $.ajax({
                url: url,
                type: 'POST',
                data: data,
                success: function (res) {
                    // console.log(res);
                    if (res.status) {
                        swal({ 
                            title: "删除成功",
                            type: 'success',
                            position: 'top',
                            timer: 3000,
                            toast: true,
                            showConfirmButton: false
                        })
                        setTimeout('location.reload()', 2000);
                    } else {
                        swal('删除出错', res.error, "error");
                    }
                }

            })


        }

    });

}
