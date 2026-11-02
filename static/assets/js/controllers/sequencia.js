angular.module('deciframeApp').controller('SequenciaController', function($http, $window, ngProgressFactory, $anchorScroll, $location, PALETA_ACORDES) {
  var vm = this;
  var corPadrao = '#2E1C74';

  vm.sequencias = [];
  vm.paletaAcordes = PALETA_ACORDES;
  vm.minhaSequencia = { acordes: [] };
  vm.isSearching = false;
  vm.showSearchResultsCount = false;
  vm.esfigeSpeech =  "";
  vm.musics = [];
  vm.generos = [];
  vm.meuGenero = "";
  vm.progressbar = ngProgressFactory.createInstance();

  vm.paginaAtual = 1;
  vm.temMais = false;
  vm.carregandoMais = false;
  vm.buscaRealizada = false;
  var idsCarregados = {};
  var buscaAtual = 0;

  vm.mostrarConstrutor = false;
  vm.sequenciaEmConstrucao = [];
  vm.nomeNovaSequencia = "";
  vm.salvando = false;
  vm.erroNovaSequencia = "";

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

  vm.carregarGeneros = function() {
    $http.get('generos')
      .success(function(data) {
        vm.generos = data;
      })
      .error(function(data) {
        vm.generos = [];
      });
  };

  vm.temAcorde = function(acorde) {
    if (vm.minhaSequencia && vm.minhaSequencia.acordes) {
      return (vm.minhaSequencia.acordes.indexOf(acorde) > -1);
    } else {
      return false;
    }
  }

  vm.alternarConstrutor = function() {
    vm.mostrarConstrutor = !vm.mostrarConstrutor;
    vm.erroNovaSequencia = "";
  };

  vm.acordeNaConstrucao = function(acorde) {
    for (var i = 0; i < vm.sequenciaEmConstrucao.length; i++) {
      if (vm.sequenciaEmConstrucao[i].acorde === acorde.acorde) {
        return true;
      }
    }
    return false;
  };

  vm.alternarAcorde = function(acorde) {
    for (var i = 0; i < vm.sequenciaEmConstrucao.length; i++) {
      if (vm.sequenciaEmConstrucao[i].acorde === acorde.acorde) {
        vm.sequenciaEmConstrucao.splice(i, 1);
        vm.erroNovaSequencia = "";
        return;
      }
    }
    vm.sequenciaEmConstrucao.push({ 'acorde': acorde.acorde, 'cor': corPadrao });
    vm.erroNovaSequencia = "";
  };

  var buscarPagina = function(pagina, acumular) {
    if (!vm.minhaSequencia || vm.minhaSequencia.id === undefined) {
      return;
    }

    var token = ++buscaAtual;

    var searchString = "similares?sequencia_id=".concat(vm.minhaSequencia.id)
      .concat("&pagina=").concat(pagina);
    if (vm.meuGenero !== "" && vm.meuGenero !== null) {
      searchString += "&generos="+vm.meuGenero;
    }

    if (acumular) {
      vm.carregandoMais = true;
    } else {
      vm.progressbar.start();
      vm.esfigeSpeech = "Procurando músicas com base na sequencia...";
      vm.isSearching = true;
      vm.musics = [];
      vm.paginaAtual = 1;
      vm.temMais = false;
      vm.buscaRealizada = false;
      idsCarregados = {};
    }

    $http.get(searchString)
      .success(function(data) {
        if (token !== buscaAtual) {
          return;
        }
        var novas = data.filter(function(musica) {
          if (idsCarregados[musica.id_unico_musica]) {
            return false;
          }
          idsCarregados[musica.id_unico_musica] = true;
          return true;
        });

        vm.progressbar.complete();
        vm.esfigeSpeech = "Encontrei essas músicas";
        vm.isSearching = false;
        vm.carregandoMais = false;
        vm.showSearchResultsCount = true;
        vm.paginaAtual = pagina;
        vm.temMais = (data.length === 100);
        vm.buscaRealizada = true;
        vm.musics = acumular ? vm.musics.concat(novas) : novas;
      })
      .error(function(data) {
        if (token !== buscaAtual) {
          return;
        }
        vm.esfigeSpeech = "Ops! Algo errado.";
        vm.isSearching = false;
        vm.carregandoMais = false;
        vm.showSearchResultsCount = false;
      });
  };

  vm.pesquisarPorSequencia = function(sequencia) {
    if (sequencia) {
      vm.minhaSequencia = sequencia;
    }
    buscarPagina(1, false);
  };

  vm.carregarMais = function() {
    if (!vm.temMais || vm.carregandoMais) {
      return;
    }
    buscarPagina(vm.paginaAtual + 1, true);
  };

  vm.salvarSequencia = function() {
    if (!vm.sequenciaEmConstrucao.length) {
      vm.erroNovaSequencia = "Adicione pelo menos um acorde.";
      return;
    }

    var payload = {
      'acordes': vm.sequenciaEmConstrucao.map(function(acorde) {
        return acorde.acorde;
      })
    };
    var nome = (vm.nomeNovaSequencia || "").trim();
    if (nome) {
      payload.nome = nome;
    }

    vm.salvando = true;
    vm.erroNovaSequencia = "";

    $http.post('sequencias', payload)
      .success(function(data) {
        vm.salvando = false;
        vm.sequenciaEmConstrucao = [];
        vm.nomeNovaSequencia = "";
        vm.mostrarConstrutor = false;
        vm.carregarCatalogo();
        vm.pesquisarPorSequencia(montarSequencia(data));
      })
      .error(function(data) {
        vm.salvando = false;
        vm.erroNovaSequencia = (data && data.erro) ? data.erro : "Não foi possível salvar a sequência.";
      });
  };

  vm.limparPesquisa = function() {
    buscaAtual += 1;
    vm.minhaSequencia = { acordes: [] };
    vm.musics = [];
    vm.buscaRealizada = false;
    vm.temMais = false;
    vm.paginaAtual = 1;
    vm.isSearching = false;
    vm.carregandoMais = false;
    vm.showSearchResultsCount = false;
    vm.esfigeSpeech = "";
    vm.progressbar.complete();
    idsCarregados = {};
  }

  vm.goToLirics = function(music) {
    $window.open(music.url);
  };

  vm.goToResults = function() {
    vm.showSearchResultsCount = false;
    $("body").animate({scrollTop: $("#results").offset().top}, "slow");
  };

  vm.carregarCatalogo();
  vm.carregarGeneros();
});
