// site/app.js
// Zajednička logika za sve prikaze. Bez frameworka i bez build-koraka.
(function (global) {
  "use strict";

  var podaci = null;

  function ucitaj() {
    if (podaci) return Promise.resolve(podaci);
    return fetch("data/ustanove.json")
      .then(function (o) {
        if (!o.ok) throw new Error("ustanove.json nije dostupan (" + o.status + ")");
        return o.json();
      })
      .then(function (json) {
        podaci = json;
        return json;
      });
  }

  // Ustanova prolazi ako ima BAREM JEDNO mjesto koje zadovoljava sve odabrane
  // filtre. Filtriranje po dobnoj skupini mora gledati pojedina mjesta, ne
  // ukupan zbroj — inače vrtić bez jaslica ispada kao da ih ima.
  function filtriraj(ustanove, f) {
    return ustanove
      .map(function (u) {
        var mjesta = u.mjesta.filter(function (m) {
          if (f.dobnaSkupina && m.dobna_skupina !== f.dobnaSkupina) return false;
          if (f.uzrast && m.uzrast !== f.uzrast) return false;
          if (f.program && m.program !== f.program) return false;
          if (f.samoSlobodna && m.slobodnih === 0) return false;
          return true;
        });
        return Object.assign({}, u, {
          mjesta: mjesta,
          slobodnih_prikaz: mjesta.reduce(function (z, m) {
            return z + m.slobodnih;
          }, 0),
        });
      })
      .filter(function (u) {
        if (f.cetvrt && u.cetvrt !== f.cetvrt) return false;
        if (f.vrsta && u.vrsta !== f.vrsta) return false;
        if (f.tekst) {
          var t = f.tekst.toLowerCase();
          var pogodak =
            u.naziv.toLowerCase().indexOf(t) !== -1 ||
            u.objekti.some(function (o) {
              return o.adresa.toLowerCase().indexOf(t) !== -1;
            });
          if (!pogodak) return false;
        }
        if (f.samoSlobodna && u.slobodnih_prikaz === 0) return false;
        return u.mjesta.length > 0;
      });
  }

  function jedinstveno(ustanove, polje) {
    var skup = {};
    ustanove.forEach(function (u) {
      if (u[polje]) skup[u[polje]] = true;
    });
    return Object.keys(skup).sort(function (a, b) {
      return a.localeCompare(b, "hr");
    });
  }

  function napuniOdabir(el, vrijednosti, svePolje) {
    el.innerHTML = "";
    var sve = document.createElement("option");
    sve.value = "";
    sve.textContent = svePolje;
    el.appendChild(sve);
    vrijednosti.forEach(function (v) {
      var o = document.createElement("option");
      o.value = v;
      o.textContent = v;
      el.appendChild(o);
    });
  }

  // Slobodna mjesta su na razini matične ustanove, ne pojedinog objekta.
  // Ova rečenica mora stajati uz svaki prikaz brojki — vidi spec, odjeljak 4.
  function oznakaRazine() {
    return "Broj slobodnih mjesta odnosi se na cijelu ustanovu, ne na pojedini objekt.";
  }

  // Podaci se mjesečno osvježavaju s gradskog portala — ime ili adresa s
  // "&", "<" ili navodnikom jednog dana neće biti iznimka. Koristiti za sve
  // podatkovne vrijednosti koje se ubacuju u HTML markup (ne za brojeve).
  function ociscen(v) {
    return String(v == null ? "" : v)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  global.VZ = {
    ucitaj: ucitaj,
    filtriraj: filtriraj,
    jedinstveno: jedinstveno,
    napuniOdabir: napuniOdabir,
    oznakaRazine: oznakaRazine,
    ociscen: ociscen,
  };
})(window);
