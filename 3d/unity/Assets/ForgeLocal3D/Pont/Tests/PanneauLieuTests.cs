using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.Linq;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using NUnit.Framework;
using UnityEngine;

namespace Forge.Pont.Tests
{
    // Lot #184 — le panneau lit un faux service local : ce qu'il montre est relu
    // nombre par nombre ; sans service, il le dit, sans zéro et sans bloquer.
    public sealed class PanneauLieuTests
    {
        private const int DELAI_MAX_PAS_MS = 100;
        private const int ATTENTE_LECTURE_MS = 10000;
        private const int LENTEUR_MS = 2000;
        private const long CELL = 1175;
        private const int ANNEE = 1400;
        private const double SEL = 12.25;
        private const long FAIM = 2;
        private const double DETTE = 40.75;
        private static readonly string[] SansArgument = { "Unity.exe" };

        private int port;
        private HttpListener ecoute;
        private Thread fil;
        private GameObject objet;
        private PanneauLieu panneau;
        private double horloge;

        [SetUp]
        public void PortLibre()
        {
            var sonde = new TcpListener(IPAddress.Loopback, 0);
            sonde.Start();
            port = ((IPEndPoint)sonde.LocalEndpoint).Port;
            sonde.Stop();
        }

        [TearDown]
        public void Fermer()
        {
            if (panneau != null) panneau.Arreter();
            if (objet != null) UnityEngine.Object.DestroyImmediate(objet);
            ecoute?.Close();
            ecoute = null;
            fil?.Join(TimeSpan.FromSeconds(5));
            fil = null;
        }

        // Un seul jeu de valeurs : le document servi et les attendus en viennent.
        private static string Document(long tick, long population, double nourriture) =>
            "{\"cell_id\":" + CELL + ",\"tick\":" + tick + ",\"date\":{\"annee\":" + ANNEE + ",\"jour_de_l_annee\":" + (tick + 1)
            + "},\"population\":" + population + ",\"stocks\":{\"sel\":" + Nombre(SEL) + ",\"nourriture\":" + Nombre(nourriture)
            + "},\"hunger_ticks\":" + FAIM + ",\"food_deficit_kg\":" + Nombre(DETTE) + "}";

        private static string Nombre(double x) => x.ToString("R", CultureInfo.InvariantCulture);

        // Rend les réponses dans l'ordre, puis répète la dernière ; `lenteur` avant chacune.
        private void Servir(int lenteur, params string[] reponses)
        {
            var file = new Queue<string>(reponses);
            string derniere = reponses.Last();
            ecoute = new HttpListener();
            ecoute.Prefixes.Add("http://127.0.0.1:" + port + "/");
            ecoute.Start();
            var auditeur = ecoute;
            fil = new Thread(() =>
            {
                while (true)
                {
                    try
                    {
                        HttpListenerContext contexte = auditeur.GetContext();
                        Thread.Sleep(lenteur);
                        byte[] octets = Encoding.UTF8.GetBytes(file.Count > 0 ? file.Dequeue() : derniere);
                        contexte.Response.StatusCode = 200;
                        contexte.Response.ContentLength64 = octets.Length;
                        contexte.Response.OutputStream.Write(octets, 0, octets.Length);
                        contexte.Response.OutputStream.Close();
                    }
                    catch (Exception) { return; }
                }
            }) { IsBackground = true };
            fil.Start();
        }

        private void Poser()
        {
            objet = new GameObject("Panneau du test");
            var camera = new GameObject("Caméra du test").AddComponent<Camera>();
            camera.transform.SetParent(objet.transform, false);
            panneau = objet.AddComponent<PanneauLieu>();
            panneau.port = port;
            panneau.camera = camera;
            panneau.Demarrer(SansArgument);
        }

        // Une lecture complète : le pas la lance, elle finit hors du fil, le pas suivant l'applique.
        private string Lire()
        {
            horloge += 1;
            panneau.Pas(horloge);
            var montre = Stopwatch.StartNew();
            while (panneau.LectureEnVol && montre.ElapsedMilliseconds < ATTENTE_LECTURE_MS) Thread.Sleep(10);
            Assert.IsFalse(panneau.LectureEnVol, "la lecture n'a pas fini");
            panneau.Pas(horloge);
            return panneau.TexteAffiche;
        }

        private static double Lu(string[] lignes, int i, string avant, string apres) =>
            double.Parse(lignes[i].Substring(avant.Length, lignes[i].Length - avant.Length - apres.Length), CultureInfo.InvariantCulture);

        private static void Verifier(string texte, long tick, long population, double nourriture)
        {
            string[] l = texte.Split('\n');
            Assert.AreEqual(7, l.Length, texte);
            Assert.AreEqual(CELL, Lu(l, 0, "Cellule ", " · tick " + tick));
            Assert.AreEqual(tick, Lu(l, 0, "Cellule " + CELL + " · tick ", ""));
            Assert.AreEqual(tick + 1, Lu(l, 1, "Date : jour ", " de " + ANNEE));
            Assert.AreEqual(ANNEE, Lu(l, 1, "Date : jour " + (tick + 1) + " de ", ""));
            Assert.AreEqual(population, Lu(l, 2, "Habitants : ", ""));
            Assert.AreEqual(nourriture, Lu(l, 3, "Nourriture : ", " kg"), "la nourriture vient en premier");
            Assert.AreEqual(SEL, Lu(l, 4, "sel : ", " kg"), "le panier se lit sans liste fermée");
            Assert.AreEqual(FAIM, Lu(l, 5, "Faim : ", " ticks de manque"));
            Assert.AreEqual(DETTE, Lu(l, 6, "Dette de nourriture : ", " kg"));
        }

        [Test]
        public void Le_panneau_affiche_les_nombres_du_faux_service()
        {
            Servir(0, Document(12, 327, 3270.5));
            Poser();

            Verifier(Lire(), 12, 327, 3270.5);
        }

        [Test]
        public void Le_panneau_se_refait_quand_le_tick_change()
        {
            Servir(0, Document(12, 327, 3270.5), Document(13, 326, 3268.5), Document(13, 326, 3268.5));
            Poser();

            string premier = Lire();
            string second = Lire();
            int apres = panneau.Reconstructions;
            string troisieme = Lire();

            Verifier(premier, 12, 327, 3270.5);
            Assert.AreNotEqual(premier, second);
            Verifier(second, 13, 326, 3268.5);
            Assert.AreEqual(second, troisieme);
            Assert.AreEqual(2, apres);
            Assert.AreEqual(apres, panneau.Reconstructions, "le même tick ne refait pas le texte");
        }

        [Test]
        public void Sans_service_le_panneau_dit_service_absent()
        {
            Poser();
            string attente = panneau.TexteAffiche;

            string texte = Lire();

            Assert.AreNotEqual(attente, texte, "la réponse du client doit remplacer l'attente");
            StringAssert.StartsWith("service absent", texte);
            StringAssert.Contains("127.0.0.1:" + port, texte);
            StringAssert.DoesNotContain("Habitants", texte);
            StringAssert.DoesNotContain("Nourriture", texte);
            Assert.AreEqual(1, panneau.Reconstructions);
        }

        [Test]
        public void Une_lecture_lente_ne_bloque_pas_la_scene()
        {
            Servir(LENTEUR_MS, Document(12, 327, 3270.5));
            Poser();
            string avant = panneau.TexteAffiche;

            var montre = Stopwatch.StartNew();
            panneau.Pas(1);
            panneau.Pas(2);
            montre.Stop();

            Assert.Less(montre.ElapsedMilliseconds, DELAI_MAX_PAS_MS, "le pas a attendu le service");
            Assert.AreEqual(avant, panneau.TexteAffiche);
        }

        [TestCase("", CELL, null)]
        [TestCase("-forgeCell 42", 42L, null)]
        [TestCase("-forgeCell abc", -1L, "abc")]
        [TestCase("-forgeCell -3", -1L, "-3")]
        [TestCase("-forgeCell", -1L, "sans valeur")]
        public void L_argument_forgeCell(string ligne, long attendue, string recu)
        {
            string[] arguments = SansArgument.Concat(ligne.Split(new[] { ' ' }, StringSplitOptions.RemoveEmptyEntries)).ToArray();

            long cellule = PanneauLieu.LireCellule(arguments, CELL, out string erreur);

            Assert.AreEqual(attendue, cellule);
            if (recu == null)
            {
                Assert.IsNull(erreur);
                return;
            }
            StringAssert.Contains("-forgeCell", erreur);
            StringAssert.Contains(recu, erreur);
        }
    }
}
