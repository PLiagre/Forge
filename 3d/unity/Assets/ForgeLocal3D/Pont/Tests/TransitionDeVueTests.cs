using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.UI;

namespace Forge.Pont.Tests {
    // Lot #728 — le fondu au noir entre deux vues, et la vitesse de la vue d'arrivée. Le faux service tient une vitesse :
    // `/horloge` la rend, `/vitesse` la change. La vitesse ne part qu'après le chargement, et jamais vers un monde en pause.
    public sealed class TransitionDeVueTests {
        private const int ATTENTE_MS = 10000; private const double PAS_S = 0.1;
        private int port; private HttpListener ecoute; private Thread fil; private GameObject objet; private TransitionDeVue transition;
        private readonly List<string> recues = new List<string>(), chargees = new List<string>();
        private double vitesse; private bool panne; private int delaiMs, recuesAuChargement; // remis à chaque cas : NUnit garde l'instance
        [SetUp] public void PortLibre() {
            var sonde = new TcpListener(IPAddress.Loopback, 0); sonde.Start(); port = ((IPEndPoint)sonde.LocalEndpoint).Port; sonde.Stop(); lock (recues) { recues.Clear(); vitesse = 2.5; panne = false; delaiMs = 0; } chargees.Clear(); recuesAuChargement = -1; }
        [TearDown] public void Fermer() {
            transition?.Arreter(); if (objet != null) UnityEngine.Object.DestroyImmediate(objet); ecoute?.Close(); fil?.Join(TimeSpan.FromSeconds(5)); (ecoute, fil, transition) = (null, null, null); }
        private void Servir() {
            var auditeur = ecoute = new HttpListener(); auditeur.Prefixes.Add("http://127.0.0.1:" + port + "/"); auditeur.Start();
            (fil = new Thread(() => { try { while (true) {
                HttpListenerContext ctx = auditeur.GetContext(); bool enPanne; int delai; string corps; lock (recues) {
                    recues.Add(ctx.Request.HttpMethod + " " + ctx.Request.Url.PathAndQuery); (enPanne, delai) = (panne, delaiMs);
                    if (ctx.Request.HttpMethod == "POST" && ctx.Request.Url.AbsolutePath == "/vitesse") vitesse = double.Parse(ctx.Request.QueryString["jours_par_seconde"], CultureInfo.InvariantCulture);
                    corps = "{\"tick\":5,\"date\":{\"annee\":1400,\"jour_de_l_annee\":6},\"jours_par_seconde\":" + vitesse.ToString("R", CultureInfo.InvariantCulture) + "}";
                }
                if (delai > 0) Thread.Sleep(delai); ctx.Response.StatusCode = enPanne ? 500 : 200; ctx.Response.Close(Encoding.UTF8.GetBytes(enPanne ? "{\"erreur\":\"panne\"}" : corps), true);
            } } catch (Exception) { } }) { IsBackground = true }).Start();
        }
        private void Commencer(string scene = "Desert_City", VueDuJeu vue = VueDuJeu.Ville) {
            objet = new GameObject("Transition du test"); transition = objet.AddComponent<TransitionDeVue>(); transition.port = port;
            transition.ChargerScene = nom => { chargees.Add(nom); recuesAuChargement = Recues().Length; }; Assert.IsTrue(transition.Commencer(scene, vue, 1));
        }
        private string[] Recues() { lock (recues) return recues.ToArray(); }
        private double VitesseServie() { lock (recues) return vitesse; } private Canvas Toile() => objet.GetComponentInChildren<Canvas>(true);
        // Des pas tous les dixièmes de seconde, chacun après la fin de la requête en vol, jusqu'à la fin de la transition.
        private List<float> Derouler(double debut = 1) { var opacites = new List<float>(); var montre = Stopwatch.StartNew();
            for (int i = 0; i < 100 && transition.EnCours; i++) {
                transition.Pas(debut + i * PAS_S); opacites.Add(transition.Opacite);
                if (transition.EnCours) Assert.IsTrue(Toile().gameObject.activeSelf, "le noir est caché pendant la transition");
                while (transition.RequeteEnVol && montre.ElapsedMilliseconds < ATTENTE_MS) Thread.Sleep(5);
            }
            Assert.IsFalse(transition.EnCours, "la transition n'a pas fini"); return opacites;
        }
        [Test] public void Les_reglages_donnent_une_annee_d_une_heure_en_ville_et_d_une_minute_sur_la_carte() {
            var r = ReglagesDesVues.Charger(); Assert.AreEqual(0.1, r.VitesseVille); Assert.AreEqual(6, r.VitesseCarte); Assert.AreEqual(0.1, r.Vitesse(VueDuJeu.Ville)); Assert.AreEqual(6, r.Vitesse(VueDuJeu.Carte));
            Assert.That(365 / r.VitesseVille / 60, Is.InRange(50, 70), "une année en ville, en minutes"); Assert.That(365 / r.VitesseCarte, Is.InRange(50, 70), "une année sur la carte, en secondes");
        }
        [TestCase("{\"VITESSE_CARTE\": 6}", "VITESSE_VILLE")] [TestCase("{\"VITESSE_VILLE\": 0.1, \"VITESSE_CARTE\": \"6\"}", "VITESSE_CARTE")]
        [TestCase("{\"VITESSE_VILLE\": 0, \"VITESSE_CARTE\": 6}", "VITESSE_VILLE")] [TestCase("{\"VITESSE_VILLE\": 0.1, \"VITESSE_CARTE\": -1}", "VITESSE_CARTE")]
        public void Un_reglage_absent_faux_ou_qui_met_en_pause_est_refuse(string json, string cle) =>
            StringAssert.Contains(cle, Assert.Catch<Exception>(() => ReglagesDesVues.Lire(json)).Message);
        [TestCase("Desert_City", VueDuJeu.Ville, "0.1")] [TestCase(OuvertureDeLaCarte.SCENE, VueDuJeu.Carte, "6")]
        public void Un_monde_qui_avance_prend_la_vitesse_de_la_vue_apres_le_chargement(string scene, VueDuJeu vue, string texte) {
            Servir(); Commencer(scene, vue); Assert.IsFalse(transition.Commencer("Autre", VueDuJeu.Carte, 1.1), "un second départ pendant l'assombrissement");
            var opacites = Derouler(); int noir = opacites.IndexOf(1); string vues = string.Join(", ", opacites);
            Assert.That(noir, Is.GreaterThan(0), "l'opacité n'atteint pas 1 : " + vues); Assert.AreEqual(0, opacites[0]); Assert.AreEqual(0, opacites[opacites.Count - 1]);
            for (int i = 1; i < opacites.Count; i++) Assert.That(i <= noir ? opacites[i] >= opacites[i - 1] : opacites[i] <= opacites[i - 1], "fondu cassé : " + vues);
            CollectionAssert.AreEqual(new[] { scene }, chargees); Assert.AreEqual(0, recuesAuChargement, "une requête est partie avant le chargement");
            CollectionAssert.AreEqual(new[] { "GET /horloge", "POST /vitesse?jours_par_seconde=" + texte }, Recues());
            Assert.AreEqual(ReglagesDesVues.Charger().Vitesse(vue), VitesseServie()); Assert.AreEqual(ReglagesDesVues.Charger().Vitesse(vue), transition.VitessePosee);
            Assert.AreEqual(scene, transition.SceneChargee); Assert.IsNull(transition.Absence);
        }
        [Test] public void Un_monde_en_pause_reste_en_pause() {
            lock (recues) vitesse = 0; Servir(); Commencer(); Derouler();
            CollectionAssert.AreEqual(new[] { "Desert_City" }, chargees); CollectionAssert.AreEqual(new[] { "GET /horloge" }, Recues());
            Assert.AreEqual(0, VitesseServie()); Assert.IsNull(transition.VitessePosee); }
        [TestCase(false)] [TestCase(true)]
        public void Une_absence_ne_bloque_ni_le_passage_ni_l_image(bool enPanne) {
            if (enPanne) { lock (recues) panne = true; Servir(); }
            Commencer(); Derouler(); Assert.AreEqual(0, transition.Opacite); CollectionAssert.AreEqual(new[] { "Desert_City" }, chargees); StringAssert.StartsWith("horloge : ", transition.Absence);
            Assert.IsFalse(Array.Exists(Recues(), r => r.StartsWith("POST", StringComparison.Ordinal)), "un réglage est parti sans horloge lue"); Assert.IsNull(transition.VitessePosee); Assert.IsFalse(Toile().gameObject.activeSelf, "le noir reste affiché au repos");
        }
        [Test] public void Un_service_lent_ne_retient_pas_l_image() {
            lock (recues) delaiMs = 500; Servir(); Commencer();
            var montre = Stopwatch.StartNew(); for (int i = 0; i < 10; i++) transition.Pas(1 + i * PAS_S); montre.Stop();
            Assert.That(montre.ElapsedMilliseconds, Is.LessThan(200), "les pas attendent le service"); CollectionAssert.AreEqual(new[] { "Desert_City" }, chargees);
        }
        [Test] public void Le_noir_couvre_tout_l_ecran_et_se_cache_au_repos() {
            Commencer(); transition.Pas(1.2); Canvas toile = Toile(); Image noir = toile.GetComponentInChildren<Image>(true);
            Assert.AreEqual(RenderMode.ScreenSpaceOverlay, toile.renderMode); Assert.AreEqual(32767, toile.sortingOrder); Assert.IsTrue(toile.gameObject.activeSelf); Assert.IsTrue(noir.raycastTarget, "le noir laisse passer les clics");
            Assert.AreEqual(0, noir.color.r); Assert.AreEqual(transition.Opacite, noir.color.a, 1e-6); Assert.That(transition.Opacite, Is.InRange(0.01f, 0.99f));
            Derouler(1.3); Assert.IsFalse(toile.gameObject.activeSelf, "le noir reste affiché au repos");
        }
        [Test] public void Lancer_cree_l_objet_et_refuse_une_seconde_transition() {
            var lancee = TransitionDeVue.Lancer("Desert_City", VueDuJeu.Carte, port); objet = lancee.gameObject; Assert.AreEqual("Transition de vue", objet.name); Assert.IsTrue(lancee.EnCours); Assert.IsNull(lancee.SceneChargee);
            Assert.IsNull(TransitionDeVue.Lancer("Desert_City", VueDuJeu.Ville, port), "une seconde transition a été lancée"); lancee.Arreter(); Assert.IsFalse(lancee.EnCours);
        }
    }
}
