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

    $.ajaxSetup({
        beforeSend: function (xhr, settings) {
            function getCookie(name) {
                var cookieValue = null;
                if (document.cookie && document.cookie != '') {
                    var cookies = document.cookie.split(';');
                    for (var i = 0; i < cookies.length; i++) {
                        var cookie = jQuery.trim(cookies[i]);
                        // Does this cookie string begin with the name we want?
                        if (cookie.substring(0, name.length + 1) == (name + '=')) {
                            cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                            break;
                        }
                    }
                }
                return cookieValue;
            }

            if (!(/^http:.*/.test(settings.url) || /^https:.*/.test(settings.url))) {
                // Only send the token to relative URLs i.e. locally.
                xhr.setRequestHeader("X-CSRFToken", getCookie('csrftoken'));
            }
        }
    });
    // Add your AJAX code here
    // ----------------
    // POST Demo
    function requestTest() {
        $.ajax({
            method: 'POST',
            url: _config.api.invokeUrl + '/api/test/',
            headers: {
                Authorization: authToken
            },
            data: JSON.stringify({
                message: "Hello, AJAX",
            }),
            contentType: 'application/json',
            success: function completeRequest(result) {
                if (result.status === "success") {
                    // do something useful here
                    alert(JSON.stringify(result.data));
                } else if (result.status === "error") {
                    alert(result.message)
                } else {
                    console.error('Error response:', JSON.stringify(result))
                }
            },
            error: function ajaxError(jqXHR, textStatus, errorThrown) {
                console.error('Error request: ', textStatus, ', Details: ', errorThrown);
                console.error('Response: ', jqXHR.responseText);
                alert('An error occured when requesting:\n' + jqXHR.responseText);
            }
        });
    }

    // ----------------

    $(function onDocReady() {
        // Trigger for AJAX function
        $('#btnTest').click(function (event) {
                event.preventDefault();
                requestTest();
            }
        );
        $('#signOut').click(function () {
            Helper.signOut();
            alert("You have been signed out.");
            window.location = "login.html";
        });
    });

}(jQuery));
