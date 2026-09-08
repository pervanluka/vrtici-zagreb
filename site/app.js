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

  var MJESECI = ["siječnja", "veljače", "ožujka", "travnja", "svibnja", "lipnja",
                 "srpnja", "kolovoza", "rujna", "listopada", "studenoga", "prosinca"];

  // "2026-09-01" -> "1. rujna 2026." Datum stanja stoji uz svaki prikaz
  // brojki; ISO oblik ostaje zapisan u podacima. Nepoznat oblik vraća se
  // neizmijenjen — bolje sirovi datum nego nikakav.
  function datumStanja(iso) {
    var d = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(iso || ""));
    if (!d) return String(iso == null ? "" : iso);
    return Number(d[3]) + ". " + MJESECI[Number(d[2]) - 1] + " " + d[1] + ".";
  }

  // Podaci se mjesečno osvježavaju s gradskog portala — ime ili adresa s
  // "&", "<" ili navodnikom jednog dana neće biti iznimka. Koristiti za sve
  // podatkovne vrijednosti koje se ubacuju u HTML markup (ne za brojeve).
  function ociscen(v) {
    return String(v == null ? "" : v)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  var MJESECI_N = ["siječanj", "veljača", "ožujak", "travanj", "svibanj", "lipanj",
                   "srpanj", "kolovoz", "rujan", "listopad", "studeni", "prosinac"];

  // "2023-03-01" -> "ožujak 2023." Za oznake na osi grafa.
  function mjesecGodina(iso) {
    var d = /^(\d{4})-(\d{2})/.exec(String(iso || ""));
    return d ? MJESECI_N[Number(d[2]) - 1] + " " + d[1] + "." : String(iso == null ? "" : iso);
  }

  // Jedan crtač za obje stranice s grafom (trend.html i ulaganja.html) — prije
  // je isti kod stajao dvaput. Snimka bez podatka NIJE nula: linija se prekida,
  // a rupa se osjenča i imenuje, da se izostanak mjerenja ne čita kao pad.
  function crtajGraf(svg, datumi, vrijednosti, naslov, opisEl) {
    var W = 1080, H = 320, GORE = 40, DOLJE = 258, LIJEVO = 72, DESNO = 1050;
    var PRVI = 180, ZADNJI = 960;
    var poznate = vrijednosti.filter(function (v) { return v !== null; });
    var max = Math.max.apply(null, poznate.concat([1]));
    var visina = DOLJE - GORE;
    var razmak = datumi.length > 1 ? (ZADNJI - PRVI) / (datumi.length - 1) : 0;

    function x(i) { return datumi.length < 2 ? (PRVI + ZADNJI) / 2 : PRVI + razmak * i; }
    function y(v) { return DOLJE - (visina * v) / max; }
    function br(n) { return n.toFixed(1); }

    var sirinaRupe = razmak ? Math.min(razmak * 0.46, 220) : 220;
    var mreza = "", osiY = "", rupe = "", crta = "", tocke = "", oznakeX = "";

    [1, 2 / 3, 1 / 3, 0].forEach(function (u) {
      var yy = br(DOLJE - visina * u);
      mreza += '<line class="mreza" x1="' + LIJEVO + '" y1="' + yy + '" x2="' + DESNO + '" y2="' + yy + '"/>';
      osiY += '<text class="oznaka" x="60" y="' + br(Number(yy) + 4) + '" text-anchor="end">' +
              Math.round(max * u) + "</text>";
    });

    var zapoceto = false;
    vrijednosti.forEach(function (v, i) {
      var datum = ociscen(datumi[i]);
      if (v === null) {
        zapoceto = false;
        rupe += '<rect class="polje-rupe" x="' + br(x(i) - sirinaRupe / 2) + '" y="' + GORE +
                '" width="' + br(sirinaRupe) + '" height="' + visina + '" rx="10"/>' +
                '<text class="natpis-rupe" x="' + br(x(i)) + '" y="' + (GORE + visina / 2 - 4) +
                '" text-anchor="middle">nema podatka</text>' +
                '<text class="oznaka" x="' + br(x(i)) + '" y="' + (GORE + visina / 2 + 15) +
                '" text-anchor="middle">' + datum.slice(0, 7) + "</text>";
        oznakeX += '<text class="oznaka" x="' + br(x(i)) + '" y="284" text-anchor="middle">' +
                   mjesecGodina(datumi[i]) + "</text>";
        return;
      }
      crta += (zapoceto ? " L" : " M") + br(x(i)) + "," + br(y(v));
      zapoceto = true;
      tocke += '<circle class="tocka" cx="' + br(x(i)) + '" cy="' + br(y(v)) + '" r="7.5"><title>' +
               datum + ": " + v + "</title></circle>" +
               '<text class="vrijednost-tocke" x="' + br(x(i)) + '" y="' + br(y(v) - 18) +
               '" text-anchor="middle">' + v + "</text>";
      oznakeX += '<text class="oznaka" x="' + br(x(i)) + '" y="284" text-anchor="middle">' +
                 mjesecGodina(datumi[i]) + "</text>";
    });

    svg.setAttribute("viewBox", "0 0 " + W + " " + H);
    svg.innerHTML = mreza + rupe + osiY +
      '<line class="os" x1="' + LIJEVO + '" y1="' + DOLJE + '" x2="' + DESNO + '" y2="' + DOLJE + '"/>' +
      '<path class="crta" d="' + crta.trim() + '"/>' + tocke + oznakeX;

    var nedostaju = datumi.filter(function (dd, i) { return vrijednosti[i] === null; });
    opisEl.textContent =
      "Slobodna mjesta — " + naslov + ". Snimaka s podatkom: " + poznate.length + "/" + datumi.length +
      (nedostaju.length ? ". Bez podatka za: " + nedostaju.join(", ") + "." : ".");
  }

  global.VZ = {
    ucitaj: ucitaj,
    filtriraj: filtriraj,
    jedinstveno: jedinstveno,
    napuniOdabir: napuniOdabir,
    oznakaRazine: oznakaRazine,
    datumStanja: datumStanja,
    mjesecGodina: mjesecGodina,
    crtajGraf: crtajGraf,
    ociscen: ociscen,
  };
})(window);
