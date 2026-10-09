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
    // Lot #525 — la date et l'horloge sur la carte. Un faux service tient un tick, une date et une vitesse : `/horloge` les
    // rend, `/vitesse` change la vitesse et rend l'horloge. Le panneau affiche ce qui est servi, et rien d'autre ; il envoie
    // la pause, la reprise et les paliers ; sans service, il le dit et n'envoie rien.
    public sealed class HorlogeDeCarteTests {
        private const int ATTENTE_MS = 10000;
        private int port; private HttpListener ecoute; private Thread fil;
        private GameObject objet; private Camera cam; private HorlogeDeCarte horloge;
        private readonly List<string> recues = new List<string>();
        private long tick, jour; private double vitesse; private bool panne; // l'état du faux service, remis à chaque cas : NUnit garde l'instance

        [SetUp] public void PortLibre() {
            var sonde = new TcpListener(IPAddress.Loopback, 0); sonde.Start(); port = ((IPEndPoint)sonde.LocalEndpoint).Port; sonde.Stop();
            lock (recues) { recues.Clear(); tick = 5; jour = 6; vitesse = 2.5; panne = false; }
        }
        [TearDown] public void Fermer() {
            horloge?.Arreter(); if (objet != null) UnityEngine.Object.DestroyImmediate(objet); if (cam != null) UnityEngine.Object.DestroyImmediate(cam.gameObject);
            ecoute?.Close(); fil?.Join(TimeSpan.FromSeconds(5)); (ecoute, fil) = (null, null);
        }

        private void Servir() {
            var auditeur = ecoute = new HttpListener(); auditeur.Prefixes.Add("http://127.0.0.1:" + port + "/"); auditeur.Start();
            (fil = new Thread(() => {
                try { while (true) {
                    HttpListenerContext ctx = auditeur.GetContext(); string chemin = ctx.Request.Url.PathAndQuery;
                    lock (recues) {
                        recues.Add(ctx.Request.HttpMethod + " " + chemin);
                        if (ctx.Request.HttpMethod == "POST" && ctx.Request.Url.AbsolutePath == "/vitesse")
                            vitesse = double.Parse(ctx.Request.QueryString["jours_par_seconde"], CultureInfo.InvariantCulture);
                    }
                    string corps = "{\"tick\":" + tick + ",\"date\":{\"annee\":1400,\"jour_de_l_annee\":" + jour + "},\"jours_par_seconde\":"
                        + vitesse.ToString("R", CultureInfo.InvariantCulture) + ",\"duree_dernier_tick_ms\":42.25,\"budget_tick_ms\":100}";
                    bool enPanne; lock (recues) enPanne = panne;
                    ctx.Response.StatusCode = enPanne ? 500 : 200; ctx.Response.Close(Encoding.UTF8.GetBytes(enPanne ? "{\"erreur\":\"panne\"}" : corps), true);
                } } catch (Exception) { }
            }) { IsBackground = true }).Start();
        }

        private void Poser() {
            cam = new GameObject("Caméra du test").AddComponent<Camera>();
            objet = new GameObject("Horloge du test"); horloge = objet.AddComponent<HorlogeDeCarte>(); horloge.port = port; horloge.Demarrer(cam);
        }

        // Quelques pas, chacun après la fin de la requête en vol, à des instants qui relancent la lecture : ce qui était
        // demandé est parti, et la réponse la plus récente du service est affichée.
        private void Pas(ref double instant) {
            var montre = Stopwatch.StartNew();
            for (int tour = 0; tour < 4; tour++) {
                horloge.Pas(instant); instant += HorlogeDeCarte.PERIODE_LECTURE_S;
                while (horloge.RequeteEnVol && montre.ElapsedMilliseconds < ATTENTE_MS) Thread.Sleep(5);
            }
            Assert.IsFalse(horloge.RequeteEnVol, "la requête n'a pas fini"); horloge.Pas(instant - HorlogeDeCarte.PERIODE_LECTURE_S / 2);
        }

        private string[] Recues() { lock (recues) return recues.ToArray(); }

        [Test] public void Les_paliers_montent_et_descendent_sans_jamais_mettre_en_pause() {
            double[] p = HorlogeDeCarte.PALIERS;
            Assert.AreEqual(p[0], HorlogeDeCarte.Suivante(0, +1)); Assert.AreEqual(p[0], HorlogeDeCarte.Suivante(0, -1));
            for (int i = 0; i + 1 < p.Length; i++) { Assert.AreEqual(p[i + 1], HorlogeDeCarte.Suivante(p[i], +1)); Assert.AreEqual(p[i], HorlogeDeCarte.Suivante(p[i + 1], -1)); }
            Assert.AreEqual(p[p.Length - 1], HorlogeDeCarte.Suivante(p[p.Length - 1], +1), "au-dessus du dernier palier");
            Assert.AreEqual(p[0], HorlogeDeCarte.Suivante(p[0], -1), "au-dessous du premier palier");
            Assert.AreEqual(5, HorlogeDeCarte.Suivante(2.5, +1)); Assert.AreEqual(2, HorlogeDeCarte.Suivante(2.5, -1));
        }

        [Test] public void Le_panneau_dit_l_horloge_servie_et_rien_d_autre() {
            Servir(); Poser(); double t = 1; Pas(ref t);
            Assert.AreEqual("Jour 6 de 1400 · tick 5\n2.5 jours par seconde", horloge.TexteAffiche);
            // Un service qui saute des jours et des ticks : le panneau recopie, il ne compte pas.
            lock (recues) { tick = 7; jour = 100; vitesse = 1; } Pas(ref t);
            Assert.AreEqual("Jour 100 de 1400 · tick 7\n1 jour par seconde", horloge.TexteAffiche);
            lock (recues) vitesse = 0; Pas(ref t);
            Assert.AreEqual("Jour 100 de 1400 · tick 7\nEn pause", horloge.TexteAffiche);
            Assert.IsTrue(Array.TrueForAll(Recues(), r => r == "GET /horloge"), "le panneau a réglé l'horloge sans qu'on le lui demande : " + string.Join(", ", Recues()));
        }

        [Test] public void Pause_reprise_et_paliers_partent_au_service() {
            Servir(); Poser(); double t = 1; Pas(ref t);
            horloge.Basculer(); Pas(ref t);
            Assert.AreEqual(0, horloge.Lue.JoursParSeconde); StringAssert.EndsWith("En pause", horloge.TexteAffiche);
            horloge.Basculer(); Pas(ref t);
            Assert.AreEqual(2.5, horloge.Lue.JoursParSeconde, "la reprise ne rend pas la vitesse d'avant la pause");
            horloge.Accelerer(); Pas(ref t); Assert.AreEqual(5, horloge.Lue.JoursParSeconde);
            horloge.Ralentir(); Pas(ref t); horloge.Ralentir(); Pas(ref t); Assert.AreEqual(1, horloge.Lue.JoursParSeconde);
            var reglages = Array.FindAll(Recues(), r => r.StartsWith("POST", StringComparison.Ordinal));
            CollectionAssert.AreEqual(new[] { "POST /vitesse?jours_par_seconde=0", "POST /vitesse?jours_par_seconde=2.5", "POST /vitesse?jours_par_seconde=5",
                "POST /vitesse?jours_par_seconde=2", "POST /vitesse?jours_par_seconde=1" }, reglages);
            Assert.AreEqual("Pause", Array.Find(objet.GetComponentsInChildren<Text>(true), x => x.name == "Libellé" && (x.text == "Pause" || x.text == "Reprendre"))?.text);
        }

        [Test] public void Sans_service_le_panneau_le_dit_et_ne_regle_rien() {
            Poser(); double t = 1; Pas(ref t);
            Assert.IsNull(horloge.Lue); StringAssert.StartsWith(CarteDessinee.MESSAGE_ABSENCE + "\n", horloge.TexteAffiche);
            Assert.IsNotNull(horloge.Absence);
            // Un service qui répond mal : l'horloge reste inconnue, et aucun réglage ne part vers un temps qu'on ne connaît pas.
            lock (recues) panne = true; Servir(); Pas(ref t);
            horloge.Basculer(); horloge.Accelerer(); horloge.Ralentir(); Pas(ref t);
            Assert.IsNull(horloge.Lue, "une horloge est apparue d'un service en panne"); StringAssert.StartsWith(CarteDessinee.MESSAGE_ABSENCE + "\n", horloge.TexteAffiche);
            Assert.IsTrue(Array.Exists(Recues(), r => r == "GET /horloge"), "le service en panne n'a pas été lu");
            Assert.IsFalse(Array.Exists(Recues(), r => r.StartsWith("POST", StringComparison.Ordinal)), "un réglage est parti sans horloge connue : " + string.Join(", ", Recues()));
            lock (recues) panne = false; Pas(ref t);
            Assert.AreEqual("Jour 6 de 1400 · tick 5\n2.5 jours par seconde", horloge.TexteAffiche, "le service revenu n'est pas relu");
        }

        [Test] public void Le_panneau_est_sur_la_camera_avec_trois_boutons() {
            Poser(); Canvas toile = objet.GetComponentInChildren<Canvas>(true);
            Assert.IsTrue(toile.renderMode == RenderMode.ScreenSpaceCamera && toile.worldCamera == cam, "le panneau n'est pas sur la caméra");
            var boutons = objet.GetComponentsInChildren<Button>(true);
            Assert.AreEqual(3, boutons.Length);
        }
    }
}
