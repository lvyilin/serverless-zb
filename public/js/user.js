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

    // Add your AJAX code here
    // ----------------
    // POST Demo
    function requestTest() {
        $.ajax({
            method: 'POST',
            url: _config.api.invokeUrl + '/api/test',
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
                alert('An error occurred when requesting:\n' + jqXHR.responseText);
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
