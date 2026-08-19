app.controller('rdcFormAnalystTipsController', ['$scope', '$rootScope', 'apiServiceV2', 'betEasyService', 'pubsub', function ($scope, $rootScope, apiServiceV2, betEasyService, pubsub) {
    function onBetAdded() {
        trackCustomAction('BetSlip', 'BetEasy - Tips', null, 'Click Win Odds');
    }

    function onBetConfirmed(response) {
        trackCustomAction('BetSlip', 'BetEasy - Tips', null, 'Bet Confirmed');
    }

    if (sitecore.betEasyUrl) {
        if (typeof $rootScope.betEasyInitialised === 'undefined') {
            $rootScope.betEasyInitialised = false;
            betEasyService.initialise(onBetAdded, onBetConfirmed);
        }

        $scope.$on('BetEasyInitialised', function (event, data) {
            $rootScope.betEasyInitialised = true;
        });
    }

    $scope.init = function () {
        $scope.widgetProps = {
            meetCode: $scope.meet,
            raceNumber: $scope.race,
            betProvider: localStorage.bookie || 'sportsbet',
            onLogin: function () {
                pubsub.publish('ShowModal', ['login']);
            },
        };
    }

    $rootScope.$on('bookie', function (ev, bookie) {
        if ($scope.widgetProps) {
            $scope.widgetProps.betProvider = bookie;
        }
    });
}]);