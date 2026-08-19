app.controller('rdcHeaderController', ['$scope', 'keyStore', 'pubsub', 'modalService', function ($scope, keyStore, pubsub, modalService) {

    $scope.init = function () {

        keyStore.get().toggleInlineVision = function () {
            $scope.change();
        };

        $scope.headerProps = {
            config: {
                app: 'website', // mega menu app
                loginEndpoint: $scope.loginEndpoint,
                logoutEndpoint: $scope.logoutEndpoint,
                killSwitchActive: $scope.killSwitchActive || false,
                toggleLiveVision: function () {
                    if ($scope.userLoggedIn || $scope.killSwitchActive) {
                        if ($scope.allowAccess || $scope.killSwitchActive) {
                            if (keyStore && keyStore.hasFunction('toggleInlineVision')) {
                                keyStore.get().toggleInlineVision();
                            }
                        } else {
                            modalService.loadUserStateModal($scope.userLoggedIn, 'liveracing');
                        }
                    } else {
                        pubsub.publish('ShowModal', ['login']);
                    }
                },
                openLoginModal: function () {
                    pubsub.publish('ShowModal', ['login']);
                },
            }
        };
    };

    $scope.change = function () {

        try {
            window.rdc?.liveVision?.ToggleLiveVision();
        }
        catch (err) {
            console.log(err.message)
        }
    };

}]);