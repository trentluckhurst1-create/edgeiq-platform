app.controller('rdcReplayHubTilesController', ['$scope', function ($scope) {
    $scope.init = function() {
        $scope.tilesProps = {
            url: $scope.feed,
        };
    }
}]);