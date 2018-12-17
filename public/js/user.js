/*global Helper _config*/

var Helper = window.Helper || {};

(function userScopeWrapper($) {
    var authToken;
    Helper.authToken.then(function setAuthToken(token) {
        if (token) {
            authToken = token;
        } else {
            window.location.href = 'login.html';
        }
    }).catch(function handleTokenError(error) {
        alert(error);
        window.location.href = 'login.html';
    });


    function requestList() {
        $.ajax({
            method: 'GET',
            url: _config.api.invokeUrl + '/api/list',
            headers: {
                Authorization: authToken
            },
            success: function completeRequest(result) {
                if (result.status === "success") {
                    // do something useful here
                    // alert(JSON.stringify(result.data));
                    var data = result.data;
                    var app = new Vue({
                        el: '#app-list',
                        data: {
                            dataset: data.dataset
                        }
                    });

                } else if (result.status === "error") {
                    alert(result.message)
                } else {
                    console.error('Error response:', JSON.stringify(result))
                }
            },
            error: function ajaxError(jqXHR, textStatus, errorThrown) {
                console.error('Error request: ', textStatus, ', Details: ', errorThrown);
                console.error('Response: ', jqXHR.responseText);
                alert('An error occurred when requesting:\n' + jqXHR.responseText);
            }
        });
    }

    function requestDetail(id, name, offset) {
        $.ajax({
            method: 'GET',
            url: _config.api.invokeUrl + '/api/detail',
            headers: {
                Authorization: authToken
            },
            data: {
                id: id,
                offset: offset,
                limit: 20
            },
            success: function completeRequest(result) {
                if (result.status === "success") {
                    // do something useful here
                    // alert(JSON.stringify(result.data));
                    var data = result.data;
                    var pageNum = Math.ceil(curDatasetSize / 20);
                    if (typeof appDetail === 'undefined') {
                        appDetail = new Vue({
                            el: '#app-detail',
                            data: {
                                name: name,
                                header: data.header,
                                records: data.records,
                                pages: Array.from(new Array(pageNum), (x, i) => i + 1)
                            }
                        });
                    } else {
                        // appDetail.data.name = name;
                        // appDetail.data.header = data.header;
                        appDetail.records = data.records;
                    }
                    $(".tag-input").val('');
                    $('#tab1').hide();
                    $("#tab3").hide();
                    $("#tab2").show();
                } else if (result.status === "error") {
                    alert(result.message)
                } else {
                    console.error('Error response:', JSON.stringify(result))
                }
            },
            error: function ajaxError(jqXHR, textStatus, errorThrown) {
                console.error('Error request: ', textStatus, ', Details: ', errorThrown);
                console.error('Response: ', jqXHR.responseText);
                alert('An error occurred when requesting:\n' + jqXHR.responseText);
            }
        });
    }

    function requestUpload() {
        $.ajax({
            method: 'POST',
            url: _config.api.invokeUrl + '/api/upload',
            headers: {
                Authorization: authToken
            },
            processData: false,
            contentType: false,
            async: false,
            cache: false,
            data: new FormData($("#uploadDatasetForm")[0]),
            success: function completeRequest(result) {
                if (result.status === "success") {
                    alert("success")
                } else if (result.status === "error") {
                    alert(result.message)
                } else {
                    console.error('Error response:', JSON.stringify(result))
                }
            },
            error: function ajaxError(jqXHR, textStatus, errorThrown) {
                console.error('Error request: ', textStatus, ', Details: ', errorThrown);
                console.error('Response: ', jqXHR.responseText);
                alert('An error occurred when requesting:\n' + jqXHR.responseText);
            }
        });
    }

    function requestAddPartner(partnerName) {
        $.ajax({
            method: 'POST',
            url: _config.api.invokeUrl + '/api/add_partner',
            headers: {
                Authorization: authToken
            },
            data: JSON.stringify({
                id: curDatasetId,
                partner: partnerName
            }),
            success: function completeRequest(result) {
                if (result.status === "success") {
                    alert("success")
                } else if (result.status === "error") {
                    alert(result.message)
                } else {
                    console.error('Error response:', JSON.stringify(result))
                }
            },
            error: function ajaxError(jqXHR, textStatus, errorThrown) {
                console.error('Error request: ', textStatus, ', Details: ', errorThrown);
                console.error('Response: ', jqXHR.responseText);
                alert('An error occurred when requesting:\n' + jqXHR.responseText);
            }
        });
    }

    function requestExport(id) {
        $.ajax({
            method: 'GET',
            url: _config.api.invokeUrl + '/api/export',
            headers: {
                Authorization: authToken
            },
            data: {
                id: id,
            },
            success: function completeRequest(result) {
                if (result.status === "success") {
                    window.open(result.data.link, '_blank');
                } else if (result.status === "error") {
                    alert(result.message)
                } else {
                    console.error('Error response:', JSON.stringify(result))
                }
            },
            error: function ajaxError(jqXHR, textStatus, errorThrown) {
                console.error('Error request: ', textStatus, ', Details: ', errorThrown);
                console.error('Response: ', jqXHR.responseText);
                alert('An error occurred when requesting:\n' + jqXHR.responseText);
            }
        });
    }

    function requestUploadTag(tags) {
        $.ajax({
            method: 'POST',
            url: _config.api.invokeUrl + '/api/tags',
            headers: {
                Authorization: authToken
            },
            data: JSON.stringify({
                id: curDatasetId,
                tags: tags
            }),
            success: function completeRequest(result) {
                if (result.status === "success") {
                    requestDetail(curDatasetId, curDatasetName, (curPage - 1) * 20);
                    alert("success");
                } else if (result.status === "error") {
                    alert(result.message)
                } else {
                    console.error('Error response:', JSON.stringify(result))
                }
            },
            error: function ajaxError(jqXHR, textStatus, errorThrown) {
                console.error('Error request: ', textStatus, ', Details: ', errorThrown);
                console.error('Response: ', jqXHR.responseText);
                alert('An error occurred when requesting:\n' + jqXHR.responseText);
            }
        });
    }

    // ----------------

    $(function onDocReady() {
        requestList();
        // Trigger for AJAX function
        $('#btnTest').click(function (event) {
            event.preventDefault();
            requestTest();
        });
        $("#uploadDatasetBtn").click(function (event) {
            event.preventDefault();
            requestUpload();
        });
        $('#signOut').click(function () {
            Helper.signOut();
            alert("You have been signed out.");
            window.location = "login.html";
        });
        $('#nav1').click(function (event) {
            event.preventDefault();
            $('#tab2').hide();
            $("#tab3").hide();
            $("#tab1").show();
        });
        $('#nav2').click(function (event) {
            event.preventDefault();
            $('#tab1').hide();
            $("#tab3").hide();
            $("#tab2").show();

        });
        $('#nav3').click(function (event) {
            event.preventDefault();
            $('#tab2').hide();
            $("#tab1").hide();
            $("#tab3").show();
        });
        $("#partnerBtn").click(function (event) {
            event.preventDefault();
            requestAddPartner($("#addPartner").val());
        });
        $(document).on('click', ".dataset-detail", function (event) {
            window.curDatasetId = this.parentNode.parentNode.firstChild.innerText;
            window.curDatasetName = this.parentNode.parentNode.childNodes[2].innerText;
            window.curDatasetSize = this.parentNode.parentNode.childNodes[4].innerText;
            window.curPage = 1;
            requestDetail(curDatasetId, curDatasetName, 0);
        });
        $(document).on('click', ".dataset-export", function (event) {
            var id = this.parentNode.parentNode.firstChild.innerText;
            requestExport(id);
        });
        $(document).on('click', "#btnUploadTag", function (event) {
            event.preventDefault();
            var rows = $("#tagTable").children();
            var tagArray = [];
            for (var i = 0; i < rows.length; ++i) {
                var tr = rows[i];
                var id = tr.firstChild.innerText;
                var tagTd = tr.getElementsByClassName("tag-input");
                var tags = [];
                for (var j = 0; j < tagTd.length; ++j) {
                    var val = tagTd[j].value;
                    if (val === "") {
                        val = tagTd[j].innerText;
                    }
                    tags.push(val);
                }
                // var tags = tr.lastChild.firstChild.value;
                tagArray.push({id: id, tag: tags});
            }
            requestUploadTag(tagArray);
        });
        $(document).on('click', ".page", function (event) {
            event.preventDefault();
            window.curPage = Number($(this).text());
            requestDetail(curDatasetId, curDatasetName, (curPage - 1) * 20);
        });
    });

}(jQuery));

