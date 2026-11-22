using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using NUnit.Framework;

namespace Forge.Pont.Tests
{
    // Le devis de la caserne relu au service : la maison du joueur, puis ses ordres ; une lecture à la fois, une par période.
    public sealed class DevisDeLaCaserneTests
    {
        const string Monde = "{\"tick\":2,\"date\":{\"annee\":1400,\"jour_de_l_annee\":3},\"cell_count\":1,\"cells\":[{\"cell_id\":10465,\"population\":1,\"hunger_ticks\":0,\"food_deficit_kg\":0}],\"maison_du_joueur\":\"seigneurie-2\"}";
        const string MondeSansMaison = "{\"tick\":2,\"date\":{\"annee\":1400,\"jour_de_l_annee\":3},\"cell_count\":1,\"cells\":[{\"cell_id\":10465,\"population\":1,\"hunger_ticks\":0,\"food_deficit_kg\":0}]}";
        // Les ordres de seigneurie-2 servis par le vrai service, le grenier trop bas pour la caserne.
        const string Ordres = "{\"armees\":[],\"cible\":null,\"date\":{\"annee\":1400,\"jour_de_l_annee\":3},\"levee\":{\"batiment\":{\"bras_par_jour\":25,\"cell_id\":10465,\"cout_kg\":2400.0,\"journees\":800,\"manque_kg\":615.5,\"nature\":\"caserne\",\"nom\":\"Caserne\",\"refus\":\"grenier insuffisant : 2400 kg de grain demandés, 1784.5 kg disponibles\"},\"grain_libre_kg\":1784.5,\"lieux\":[{\"cell_id\":10465,\"hommes_max\":619,\"rang\":0}],\"paysans\":79950,\"ration_kg_par_homme_par_jour\":2.5,\"refus\":null},\"maison\":\"seigneurie-2\",\"tick\":2}";

        int port; HttpListener ecoute; Thread fil; readonly List<string> recues = new();
        [SetUp] public void PortLibre() { var s = new TcpListener(IPAddress.Loopback, 0); s.Start(); port = ((IPEndPoint)s.LocalEndpoint).Port; s.Stop(); lock (recues) recues.Clear(); }
        [TearDown] public void Fermer() { ecoute?.Close(); fil?.Join(TimeSpan.FromSeconds(5)); (ecoute, fil) = (null, null); }

        // Sert `monde` sur /monde et `ordres` sur /guerres/ordres.
        void Servir(string monde, string ordres)
        {
            var a = ecoute = new HttpListener(); a.Prefixes.Add("http://127.0.0.1:" + port + "/"); a.Start();
            (fil = new Thread(() => {
                try { while (true) { var c = a.GetContext(); lock (recues) recues.Add(c.Request.RawUrl);
                    byte[] octets = Encoding.UTF8.GetBytes(c.Request.Url.AbsolutePath == "/monde" ? monde : ordres);
                    c.Response.StatusCode = 200; c.Response.ContentLength64 = octets.Length; c.Response.OutputStream.Write(octets, 0, octets.Length); c.Response.Close(); } }
                catch (Exception) { }
            })).Start();
        }
        int Recues() { lock (recues) return recues.Count; }

        // Avance l'horloge du test jusqu'à ce qu'une lecture soit recueillie ; rend l'instant atteint.
        static double Recueillir(DevisDeLaCaserne devis, double instant)
        {
            var montre = Stopwatch.StartNew();
            while (!devis.Pas(instant)) { Assert.Less(montre.Elapsed.TotalSeconds, 10, "aucune lecture recueillie"); Thread.Sleep(10); }
            return instant;
        }

        [Test] public void Le_devis_est_celui_de_la_maison_du_joueur_tel_que_servi()
        {
            Servir(Monde, Ordres);
            var devis = new DevisDeLaCaserne(port);
            Assert.IsNull(devis.Devis); Assert.IsNotNull(devis.Absence);
            Recueillir(devis, 0);
            Assert.IsNull(devis.Absence, devis.Absence);
            Assert.AreEqual(615.5, devis.Devis.ManqueKg); Assert.AreEqual(2400.0, devis.Devis.CoutKg);
            lock (recues) CollectionAssert.AreEqual(new[] { "/monde", "/guerres/ordres?maison=seigneurie-2" }, recues);
        }

        [Test] public void Une_lecture_a_la_fois_et_une_par_periode()
        {
            Servir(Monde, Ordres);
            var devis = new DevisDeLaCaserne(port);
            devis.Pas(0); Assert.IsTrue(devis.RequeteEnVol);
            Recueillir(devis, 0.1); Assert.AreEqual(1, devis.Lectures);
            // La période n'est pas passée : rien ne part.
            for (int i = 0; i < 20; i++) { devis.Pas(0.5); Thread.Sleep(5); }
            Assert.AreEqual(2, Recues()); Assert.IsFalse(devis.RequeteEnVol);
            devis.Pas(DevisDeLaCaserne.PERIODE_S + 0.1); Assert.IsTrue(devis.RequeteEnVol);
            Recueillir(devis, DevisDeLaCaserne.PERIODE_S + 0.2); Assert.AreEqual(4, Recues());
            // Après un dépôt, la relecture part sans attendre la période.
            devis.Relire(); devis.Pas(DevisDeLaCaserne.PERIODE_S + 0.3); Assert.IsTrue(devis.RequeteEnVol);
        }

        [Test] public void Sans_maison_choisie_le_devis_nomme_son_absence()
        {
            Servir(MondeSansMaison, Ordres);
            var devis = new DevisDeLaCaserne(port);
            Recueillir(devis, 0);
            Assert.IsNull(devis.Devis); Assert.AreEqual("aucune maison choisie", devis.Absence);
            Assert.AreEqual(1, Recues(), "sans maison, les ordres ne se lisent pas");
        }

        [Test] public void Sans_service_le_devis_nomme_son_absence()
        {
            var devis = new DevisDeLaCaserne(port);
            Recueillir(devis, 0);
            Assert.IsNull(devis.Devis); StringAssert.StartsWith("monde : ", devis.Absence);
        }
    }
}
