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
        private const int STATUT_OK = 200;
        private const int STATUT_INTROUVABLE = 404;
        private const long CELL = 1175;
        private const int ANNEE = 1400;
        private const double SEL = 12.25;
        private const long FAIM = 2;
        private const double DETTE = 40.75;
        private static readonly string[] SansArgument = { "Unity.exe" };

        // Le seul jeu de valeurs : le document servi et les attendus en viennent tous deux.
        private sealed class Etat
        {
            public readonly long Tick, Jour, Population;
            public readonly double Nourriture;
            public Etat(long tick, long jour, long population, double nourriture)
            {
                Tick = tick; Jour = jour; Population = population; Nourriture = nourriture;
            }
        }

        private static readonly Etat Tick12 = new Etat(12, 13, 327, 3270.5);
        private static readonly Etat Tick13 = new Etat(13, 14, 326, 3268.5);

        private int port;
        private int requetes;
        private volatile string derniereRequete;
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
            requetes = 0;
            derniereRequete = null;
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

        // Les champs du document, dans l'ordre ; `sans` en retire un (une clé manquante).
        private static string Document(Etat e, string sans = null)
        {
            var champs = new List<KeyValuePair<string, string>>
            {
                new KeyValuePair<string, string>("cell_id", Entier(CELL)),
                new KeyValuePair<string, string>("tick", Entier(e.Tick)),
                new KeyValuePair<string, string>("date", "{\"annee\":" + Entier(ANNEE) + ",\"jour_de_l_annee\":" + Entier(e.Jour) + "}"),
                new KeyValuePair<string, string>("population", Entier(e.Population)),
                new KeyValuePair<string, string>("stocks", "{\"sel\":" + Nombre(SEL) + ",\"nourriture\":" + Nombre(e.Nourriture) + "}"),
                new KeyValuePair<string, string>("hunger_ticks", Entier(FAIM)),
                new KeyValuePair<string, string>("food_deficit_kg", Nombre(DETTE)),
            };
            return "{" + string.Join(",", champs.Where(c => c.Key != sans).Select(c => "\"" + c.Key + "\":" + c.Value)) + "}";
        }

        private static string Nombre(double x) => x.ToString("R", CultureInfo.InvariantCulture);
        private static string Entier(long x) => x.ToString(CultureInfo.InvariantCulture);
        private static (int, string) Ok(string corps) => (STATUT_OK, corps);

        // Rend les réponses dans l'ordre, puis répète la dernière ; `lenteur` avant chacune.
        // Chaque requête reçue est comptée avant toute réponse.
        private void Servir(int lenteur, params (int statut, string corps)[] reponses)
        {
            var file = new Queue<(int statut, string corps)>(reponses);
            var derniere = reponses.Last();
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
                        derniereRequete = contexte.Request.Url.PathAndQuery;
                        Interlocked.Increment(ref requetes);
                        Thread.Sleep(lenteur);
                        var reponse = file.Count > 0 ? file.Dequeue() : derniere;
                        byte[] octets = Encoding.UTF8.GetBytes(reponse.corps);
                        contexte.Response.StatusCode = reponse.statut;
                        contexte.Response.ContentLength64 = octets.Length;
                        contexte.Response.OutputStream.Write(octets, 0, octets.Length);
                        contexte.Response.OutputStream.Close();
                    }
                    catch (Exception) { return; }
                }
            }) { IsBackground = true };
            fil.Start();
        }

        private void Poser(params string[] arguments)
        {
            objet = new GameObject("Panneau du test");
            var camera = new GameObject("Caméra du test").AddComponent<Camera>();
            camera.transform.SetParent(objet.transform, false);
            panneau = objet.AddComponent<PanneauLieu>();
            panneau.port = port;
            panneau.camera = camera;
            panneau.Demarrer(SansArgument.Concat(arguments).ToArray());
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

        // Relit une ligne : chaque libellé est comparé tel quel, à sa place, et les nombres
        // entre deux libellés sont relus en InvariantCulture. Un libellé vide ferme la ligne.
        private static double[] Relire(string ligne, params string[] libelles)
        {
            Assert.IsTrue(ligne.StartsWith(libelles[0], StringComparison.Ordinal), "« " + libelles[0] + " » attendu en tête de : " + ligne);
            int pos = libelles[0].Length;
            var nombres = new double[libelles.Length - 1];
            for (int k = 1; k < libelles.Length; k++)
            {
                bool dernier = k == libelles.Length - 1;
                int fin = dernier ? ligne.Length - libelles[k].Length : ligne.IndexOf(libelles[k], pos, StringComparison.Ordinal);
                Assert.Greater(fin, pos, "« " + libelles[k] + " » attendu après un nombre dans : " + ligne);
                Assert.AreEqual(libelles[k], ligne.Substring(fin, libelles[k].Length), "libellé faux dans : " + ligne);
                nombres[k - 1] = double.Parse(ligne.Substring(pos, fin - pos), NumberStyles.Float, CultureInfo.InvariantCulture);
                pos = fin + libelles[k].Length;
            }
            Assert.AreEqual(ligne.Length, pos, "texte en trop dans : " + ligne);
            return nombres;
        }

        private static void Verifier(string texte, Etat e)
        {
            string[] l = texte.Split('\n');
            Assert.AreEqual(7, l.Length, texte);
            CollectionAssert.AreEqual(new double[] { CELL, e.Tick }, Relire(l[0], "Cellule ", " · tick ", ""));
            CollectionAssert.AreEqual(new double[] { e.Jour, ANNEE }, Relire(l[1], "Date : jour ", " de ", ""));
            CollectionAssert.AreEqual(new double[] { e.Population }, Relire(l[2], "Habitants : ", ""));
            CollectionAssert.AreEqual(new[] { e.Nourriture }, Relire(l[3], "Nourriture : ", " kg"), "la nourriture vient en premier");
            CollectionAssert.AreEqual(new[] { SEL }, Relire(l[4], "sel : ", " kg"), "le panier se lit sans liste fermée");
            CollectionAssert.AreEqual(new double[] { FAIM }, Relire(l[5], "Faim : ", " ticks de manque"));
            CollectionAssert.AreEqual(new[] { DETTE }, Relire(l[6], "Dette de nourriture : ", " kg"));
        }

        private static void SansNombre(string texte)
        {
            StringAssert.DoesNotContain("Habitants", texte);
            StringAssert.DoesNotContain("Nourriture", texte);
        }

        [Test]
        public void Le_panneau_affiche_les_nombres_du_faux_service()
        {
            Servir(0, Ok(Document(Tick12)));
            Poser();

            Verifier(Lire(), Tick12);
        }

        [Test]
        public void Le_panneau_se_refait_quand_le_tick_change()
        {
            Servir(0, Ok(Document(Tick12)), Ok(Document(Tick13)), Ok(Document(Tick13)));
            Poser();

            string premier = Lire();
            string second = Lire();
            int apres = panneau.Reconstructions;
            string troisieme = Lire();

            Verifier(premier, Tick12);
            Assert.AreNotEqual(premier, second);
            Verifier(second, Tick13);
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
            SansNombre(texte);
            Assert.AreEqual(1, panneau.Reconstructions);
        }

        // Une 404 (même si son corps dit « service absent »), un JSON invalide ou une clé
        // manquante : le service a répondu, le lieu est illisible, et les nombres d'avant partent.
        [TestCase("404")]
        [TestCase("json")]
        [TestCase("cle")]
        public void Une_reponse_illisible_dit_lieu_illisible(string cas)
        {
            (int, string) illisible =
                cas == "404" ? (STATUT_INTROUVABLE, "service absent : aucun lieu pour cette cellule")
                : cas == "json" ? Ok("{\"cell_id\":" + Entier(CELL) + ",")
                : Ok(Document(Tick12, sans: "population"));
            Servir(0, Ok(Document(Tick12)), illisible);
            Poser();

            Verifier(Lire(), Tick12);
            string texte = Lire();

            StringAssert.StartsWith("lieu illisible : ", texte);
            SansNombre(texte);
            Assert.AreEqual(2, panneau.Reconstructions);
        }

        [Test]
        public void Une_lecture_lente_ne_bloque_pas_la_scene()
        {
            Servir(LENTEUR_MS, Ok(Document(Tick12)));
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

        // Le panneau lui-même : une valeur refusée s'affiche et aucune requête ne part,
        // jamais de repli sur 1175 ; une valeur valable est bien celle demandée au service.
        [TestCase("-forgeCell abc", "abc")]
        [TestCase("-forgeCell -3", "-3")]
        [TestCase("-forgeCell", "sans valeur")]
        public void Une_cellule_refusee_s_affiche_et_n_interroge_pas_le_service(string ligne, string recu)
        {
            Servir(0, Ok(Document(Tick12)));
            Poser(ligne.Split(' '));

            string texte = Lire();

            StringAssert.StartsWith("-forgeCell", texte);
            StringAssert.Contains(recu, texte);
            SansNombre(texte);
            Assert.AreEqual(0, Volatile.Read(ref requetes), "le service a été interrogé malgré une cellule refusée");
        }

        [Test]
        public void La_cellule_de_forgeCell_est_celle_demandee_au_service()
        {
            Servir(0, Ok(Document(Tick12)));
            Poser("-forgeCell", "42");

            Lire();

            Assert.AreEqual(1, Volatile.Read(ref requetes));
            Assert.AreEqual("/lieu?cell=42", derniereRequete);
        }
    }
}
