/*
 * This file is part of invenio.
 * Copyright (C) 2016 CERN.
 *
 * invenio is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public License as
 * published by the Free Software Foundation; either version 2 of the
 * License, or (at your option) any later version.
 *
 * invenio is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with invenio; if not, write to the Free Software Foundation, Inc.,
 * 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.
 *
 * In applying this license, CERN does not
 * waive the privileges and immunities granted to it by virtue of its status
 * as an Intergovernmental Organization or submit itself to any jurisdiction.
 */

function invenioRecordsController($scope, $q, invenioRecordsAPI) {
  var vm = this;

  // The request args
  vm.invenioRecordsArgs = {
    url: '/',
    method: 'GET'
  };

  // The form model
  vm.invenioRecordsModel = {};
  // Set loading
  vm.invenioRecordsLoading = true;
  // Set endpoints
  vm.invenioRecordsEndpoints = {};
  // Set errors
  vm.invenioRecordsError = {};
  // Set notify
  vm.invenioRecordsNotify = false;

  function invenioRecordsSetSchema(response) {
    vm.invenioRecordsSchema = response.data;
  }

  function invenioRecordsSetForm(response) {
    vm.invenioRecordsForm = response.data;
  }

  function invenioRecordsInitialize(evt, args, endpoints, record) {

    // Assign the model
    vm.invenioRecordsModel = angular.copy(record);
    // Assign the args
    vm.invenioRecordsArgs = angular.merge(
      {},
      vm.invenioRecordsArgs,
      args
    );
    vm.invenioRecordsEndpoints = angular.merge(
      {},
      endpoints
    );

    // Get the schema and the form
    $q.all([
      invenioRecordsAPI.get(vm.invenioRecordsEndpoints.schema).then(
        invenioRecordsSetSchema
      ),
      invenioRecordsAPI.get(vm.invenioRecordsEndpoints.form).then(
        invenioRecordsSetForm
      )
    ]).then(function() {
      vm.invenioRecordsLoading = false;
    });
  }

  // FIXME: Add me to a nice factory :)
  function invenioRecordsActions(evt, args, successCallback, errorCallback) {
    vm.invenioRecordsLoading = true;
    // Reset any errors
    vm.invenioRecordsError = {};
    // Reset any notifications
    vm.invenioRecordsNotify = false;
    // Make the request
    invenioRecordsAPI.request(args)
      .then(
        successCallback || angular.noop,
        errorCallback || angular.noop
      ).finally(function() {
        vm.invenioRecordsLoading = false;
      });
  }

  function actionSave() {
    // POST
    var args = angular.copy(vm.invenioRecordsArgs);
    args.data = angular.copy(vm.invenioRecordsModel);
    args.method = 'PUT';

    function _successfulSave(response) {
      vm.invenioRecordsNotify = response.data || 'Success';
    }
    function _erroredSave(response) {
      vm.invenioRecordsError = response;
    }

    $scope.$broadcast(
      'invenio.records.action', args, _successfulSave, _erroredSave
    );
  }

  function actionDelete() {
    // DELETE
    var args = angular.copy(vm.invenioRecordsArgs);
    args.method = 'DELETE';

    function _successfulDelete(response) {
      console.log('Deleting....', response);
      vm.invenioRecordsNotify = response.data || 'Successfully deleted!';
    }
    function _erroredDelete(response) {
      vm.invenioRecordsError = response;
    }
    $scope.$broadcast(
      'invenio.records.action', args, _successfulDelete, _erroredDelete
    );
  }

  // Attach fuctions to the scope

  vm.actionSave = actionSave;
  vm.actionDelete = actionDelete;

  // Event listeners

  $scope.$on(
    'invenio.records.initialization', invenioRecordsInitialize
  )
  $scope.$on(
    'invenio.records.action', invenioRecordsActions
  )
}

invenioRecordsController.$inject = ['$scope', '$q', 'invenioRecordsAPI'];

function invenioRecordsAPI($http) {

  function request(args) {
    return $http(args);
  }

  function get(url) {
    var args = {
      url: url,
      method: 'GET'
    };
    return request(args);
  }
  return {
    get: get,
    request: request,
  }
}

invenioRecordsAPI.$inject = ['$http'];

function invenioRecords() {

  function link(scope, element, attrs, vm) {

    var collectedArgs = {
      url: attrs.actionEndpoint,
      method: attrs.actionMethod || 'GET'
    }

    var extraParams = {
      params: JSON.parse(attrs.extraParams || '{}')
    }

    var args = angular.merge(
      {},
      collectedArgs,
      extraParams
    );
    // Endpoints
    var endpoints = {
      schema: attrs.schema,
      form: attrs.form
    }

    var record = JSON.parse(attrs.record || '{}');
    // Spread the love of initialization
    scope.$broadcast(
      'invenio.records.initialization', args, endpoints, record
    );
  }

  return {
    restrict: 'AE',
    scope: false,
    controller: 'invenioRecordsController',
    controllerAs: 'vm',
    link: link,
  };
}

function invenioRecordsActions() {

  function templateUrl(element, attrs) {
    return attrs.template;
  }
  return {
    restrict: 'AE',
    scope: false,
    require: '^invenioRecords',
    templateUrl: templateUrl,
  };
}

function invenioRecordsForm() {

  function templateUrl(element, attrs) {
    return attrs.template;
  }
  return {
    restrict: 'AE',
    scope: false,
    require: '^invenioRecords',
    templateUrl: templateUrl,
  };
}

///////////////

// Controllers
angular.module('invenioRecords.controllers', [])
  .controller('invenioRecordsController', invenioRecordsController);

// Services
angular.module('invenioRecords.services', [])
  .service('invenioRecordsAPI', invenioRecordsAPI);

// Directives
angular.module('invenioRecords.directives', [])
  .directive('invenioRecords', invenioRecords)
  .directive('invenioRecordsActions', invenioRecordsActions)
  .directive('invenioRecordsForm', invenioRecordsForm);

// FIXME: I'm ugly, gimme a nip tuck
angular.module('invenioRecords' , [
  'invenioRecords.services',
  'invenioRecords.controllers',
  'invenioRecords.directives',
]);

// HAPPY RECORD EDITING :) & Please fix me!

// Bootstrap it!
angular.element(document).ready(function() {
  angular.bootstrap(
    document.getElementById("invenio-records"),
    ['invenioRecords', 'schemaForm']
  );
});
