angular.module('deciframeApp').controller('SequenciaController', function($http, $window, ngProgressFactory, $anchorScroll, $location, GENEROS, PALETA_ACORDES) {
  var vm = this;
  var corPadrao = '#2E1C74';

  vm.sequencias = [];
  vm.paletaAcordes = [].concat.apply([], PALETA_ACORDES);
  vm.minhaSequencia = {};
  vm.isSearching = false;
  vm.showSearchResultsCount = false;
  vm.esfigeSpeech =  "";
  vm.musics = [];
  vm.generos = GENEROS;
  vm.meuGenero = "";
  vm.progressbar = ngProgressFactory.createInstance();

  var montarSequencia = function(linha) {
    return {
      'id': linha.id,
      'nome': linha.nome,
      'origem': linha.origem,
      'acordes': linha.acordes.split(';').map(function(acorde) {
        return { 'acorde': acorde, 'cor': corPadrao };
      })
    };
  };

  vm.carregarCatalogo = function() {
    $http.get('sequencias')
      .success(function(data) {
        vm.sequencias = data.map(montarSequencia);
      })
      .error(function(data) {
        vm.sequencias = [];
      });
  };

  vm.temAcorde = function(acorde) {
    if (vm.minhaSequencia && vm.minhaSequencia.acordes) {
      return (vm.minhaSequencia.acordes.indexOf(acorde) > -1);
    } else {
      return false;
    }
  }

  vm.pesquisarPorSequencia = function(sequencia) {
    if (sequencia) {
      vm.minhaSequencia = sequencia;
    }
    if (!vm.minhaSequencia || vm.minhaSequencia.id === undefined) {
      return;
    }

    vm.progressbar.start();
    vm.esfigeSpeech = "Procurando músicas com base na sequencia...";
    vm.isSearching = true;
    vm.musics = [];

    var apiUrl = "";
    var searchString = "similares?sequencia_id=".concat(vm.minhaSequencia.id);
    if (vm.meuGenero !== "" && vm.meuGenero !== null) {
      searchString += "&generos="+vm.meuGenero;
    }
    $http.get(apiUrl.concat(searchString))
      .success(function(data) {
        vm.progressbar.complete();
        vm.esfigeSpeech = "Encontrei essas músicas";
        vm.isSearching = false;
        vm.showSearchResultsCount = true;
        vm.musics = data;
      })
      .error(function(data) {
        vm.esfigeSpeech = "Ops! Algo errado.";
        vm.isSearching = false;
        vm.showSearchResultsCount = false;
      });
  }

  vm.limparPesquisa = function() {
    vm.minhaSequencia = {};
    vm.musics = [];
  }

  vm.goToLirics = function(music) {
    $window.open(music.url);
  };

  vm.goToResults = function() {
    vm.showSearchResultsCount = false;
    $("body").animate({scrollTop: $("#results").offset().top}, "slow");
  };

  vm.carregarCatalogo();
});
