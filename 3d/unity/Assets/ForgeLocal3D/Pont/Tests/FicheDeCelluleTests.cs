using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using NUnit.Framework;
using UnityEngine;

namespace Forge.Pont.Tests {
    // Lot #526 — le survol d'une cellule ouvre sa fiche. Un faux service sert la carte de la graine 0 (`/carte`) et un monde
    // de deux cellules (`/monde`) : Metz (10437) et une cellule à la faim non calculée ; les autres en sont absentes.
    // Le repérage trouve la cellule sous chaque triangle de la carte, trous compris ; la fiche recopie ce qui est servi.
    public sealed class FicheDeCelluleTests {
        private const int ATTENTE_MS = 20000; private const long METZ = 10437;
        private int port; private HttpListener ecoute; private Thread fil; private volatile string monde; private volatile int statutMonde;
        private GameObject objet; private CarteDessinee carte; private FicheDeCellule fiche;
        private static byte[] Fixture => File.ReadAllBytes(Application.dataPath + "/ForgeLocal3D/Pont/Tests/carte-graine0.json");

        [SetUp] public void PortLibre() {
            var sonde = new TcpListener(IPAddress.Loopback, 0); sonde.Start(); port = ((IPEndPoint)sonde.LocalEndpoint).Port; sonde.Stop();
            statutMonde = 200; monde = null;
        }
        [TearDown] public void Fermer() {
            fiche?.Arreter(); carte?.Arreter(); if (objet != null) UnityEngine.Object.DestroyImmediate(objet);
            ecoute?.Close(); fil?.Join(TimeSpan.FromSeconds(5)); (ecoute, fil) = (null, null);
        }

        // Metz et `autre` (faim et dette non calculées) ; toute autre cellule est absente de ce monde.
        private static string Monde(long autre) =>
            "{\"tick\":30,\"date\":{\"annee\":1400,\"jour_de_l_annee\":31},\"cell_count\":2,\"cells\":["
            + "{\"cell_id\":" + METZ + ",\"population\":1234,\"hunger_ticks\":2,\"food_deficit_kg\":12.5},"
            + "{\"cell_id\":" + autre + ",\"population\":0,\"hunger_ticks\":-1,\"food_deficit_kg\":-1}]}";

        private void Servir() {
            monde = Monde(1);
            byte[] carteServie = Fixture; var auditeur = ecoute = new HttpListener(); auditeur.Prefixes.Add("http://127.0.0.1:" + port + "/"); auditeur.Start();
            (fil = new Thread(() => {
                try { while (true) {
                    HttpListenerContext ctx = auditeur.GetContext(); bool estCarte = ctx.Request.Url.AbsolutePath == "/carte";
                    byte[] corps = estCarte ? carteServie : Encoding.UTF8.GetBytes(monde);
                    ctx.Response.StatusCode = estCarte ? 200 : statutMonde; ctx.Response.Close(corps, true);
                } } catch (Exception) { }
            }) { IsBackground = true }).Start();
        }

        private CarteLue Lue() {
            LectureCarte lecture; using (var client = new ClientCarte(port, ClientCarte.DelaiMinimal)) lecture = client.Lire();
            Assert.IsTrue(lecture.Presente, lecture.Absence); return lecture.Carte;
        }

        // La carte posée et le monde lu, comme en jeu : la carte d'abord, la fiche ensuite.
        private void Poser() {
            objet = new GameObject("Carte du test"); carte = objet.AddComponent<CarteDessinee>(); carte.port = port; carte.Demarrer();
            fiche = objet.AddComponent<FicheDeCellule>(); fiche.port = port; fiche.Demarrer();
            var montre = Stopwatch.StartNew(); double t = 1;
            bool lus() => carte.CellulesServies > 0 && (fiche.MondeLu != null || fiche.AbsenceDuMonde != null);
            while (!lus() && montre.ElapsedMilliseconds < ATTENTE_MS) { carte.Pas(t); fiche.Pas(t); t += 0.5; Thread.Sleep(10); }
            Assert.IsTrue(lus(), "la carte ou le monde n'a pas été lu : " + carte.TexteAffiche);
        }

        // Le milieu du plus grand triangle de la cellule, en local : un point bien à elle. Les éclats d'un ou deux mètres
        // posés sur son bord n'en sont pas : en km et en float, leur milieu peut tomber de l'autre côté du bord.
        private static Vector3 Milieu(MaillageDeCellule c) {
            var s = c.Maillage.Sommets; var t = c.Maillage.Triangles; int meilleur = 0; float aire = -1;
            for (int k = 0; k < t.Count; k += 3) {
                float a = Vector3.Cross(s[t[k + 1]] - s[t[k]], s[t[k + 2]] - s[t[k]]).magnitude;
                if (a > aire) { aire = a; meilleur = k; }
            }
            return (s[t[meilleur]] + s[t[meilleur + 1]] + s[t[meilleur + 2]]) / 3;
        }

        private Vector3 DansLaCellule(CarteMaillee maillee, long cellId) => objet.transform.TransformPoint(Milieu(maillee.Cellules.First(x => x.CellId == cellId)));

        // Un anneau servi, en km locaux, converti comme les contours (#548) : ((x - origine) / 1000), x vers l'est, z vers le nord.
        private static Vector2[] Local(IReadOnlyList<PointCarte> anneau, PointCarte origine) =>
            anneau.Select(p => new Vector2((float)((p.X - origine.X) / 1000.0), (float)((p.Y - origine.Y) / 1000.0))).ToArray();

        // Le point (x, z) est-il dans l'anneau (règle pair-impair) ?
        private static bool DansAnneau(Vector2[] anneau, float x, float z) {
            bool dedans = false;
            for (int i = 0, j = anneau.Length - 1; i < anneau.Length; j = i++) {
                Vector2 a = anneau[i], b = anneau[j];
                if ((a.y > z) != (b.y > z) && x < (double)(b.x - a.x) * (z - a.y) / (b.y - a.y) + a.x) dedans = !dedans;
            }
            return dedans;
        }

        [Test] public void Chaque_cellule_est_sous_son_milieu_et_ses_trous_n_en_sont_pas() {
            Servir(); CarteLue lue = Lue(); CarteMaillee maillee = MaillageDeCarte.Mailler(lue); var reperage = new ReperageDeCarte(lue, maillee.Origine);
            int cellules = 0;
            foreach (MaillageDeCellule c in maillee.Cellules) {
                Vector3 m = Milieu(c); cellules++;
                CelluleDeCarte sous = reperage.Sous(m.x, m.z);
                if (sous == null || sous.CellId != c.CellId) Assert.Fail("le milieu de la cellule " + c.CellId + " est repéré dans " + (sous == null ? "la mer" : "la cellule " + sous.CellId));
            }
            Assert.AreEqual(lue.Cellules.Count, cellules);
            // Un point dans un trou (un lac, une enclave) n'est pas à la cellule qui l'entoure : il est à la mer, ou à l'enclave.
            int trous = 0, eprouves = 0;
            foreach (CelluleDeCarte c in lue.Cellules) foreach (PolygoneDeCarte p in c.Contour) foreach (var brut in p.Trous) {
                Vector2[] trou = Local(brut, maillee.Origine); trous++;
                float xMin = trou.Min(q => q.x), xMax = trou.Max(q => q.x), zMin = trou.Min(q => q.y), zMax = trou.Max(q => q.y);
                bool trouve = false;
                for (int i = 1; i < 10 && !trouve; i++) for (int j = 1; j < 10 && !trouve; j++) {
                    float x = xMin + (xMax - xMin) * i / 10, z = zMin + (zMax - zMin) * j / 10;
                    if (!DansAnneau(trou, x, z)) continue;
                    trouve = true; eprouves++;
                    CelluleDeCarte sous = reperage.Sous(x, z);
                    Assert.IsTrue(sous == null || sous.CellId != c.CellId, "un point d'un trou de la cellule " + c.CellId + " est repéré dans cette cellule");
                }
            }
            Assert.Greater(trous, 0, "la carte n'a pas de trou : le cas n'est pas éprouvé");
            Assert.Greater(eprouves, trous / 2, eprouves + " trous éprouvés sur " + trous);
            Assert.IsNull(reperage.Sous(1e6f, 1e6f), "un point hors de la carte est dans une cellule");
        }

        [Test] public void La_fiche_dit_la_carte_et_le_monde_servis() {
            Servir(); CarteLue lue = Lue();
            long autre = lue.Cellules.First(c => c.CellId != METZ && c.Maison != null && c.Puissance != null).CellId;
            long absente = lue.Cellules.First(c => c.CellId != METZ && c.CellId != autre).CellId;
            monde = Monde(autre); Poser(); CarteMaillee maillee = MaillageDeCarte.Mailler(lue);
            CelluleDeCarte metz = lue.Cellules.First(c => c.CellId == METZ), deux = lue.Cellules.First(c => c.CellId == autre);
            Assert.IsTrue(metz.Villes.Any(v => v.Nom == "Metz") && metz.Maison == null && metz.Puissance != null, "la fixture a changé : Metz n'est plus le témoin d'une maison absente");

            fiche.SurvolerPoint(DansLaCellule(maillee, METZ));
            Assert.AreEqual(METZ, fiche.Survolee?.CellId);
            Assert.AreEqual("Cellule 10437 · Metz\nPuissance : " + metz.Puissance.Nom + "\nMaison : aucune, le monde n'en nomme pas\nHabitants : 1234 au tick 30\nFaim : 2 ticks de manque\nDette de nourriture : 12.5 kg", fiche.TexteAffiche);

            fiche.SurvolerPoint(DansLaCellule(maillee, autre));
            StringAssert.Contains("\nPuissance : " + deux.Puissance.Nom + "\nMaison : " + deux.Maison.Nom + "\nHabitants : 0 au tick 30\nFaim : non calculée\nDette de nourriture : non calculée", fiche.TexteAffiche);
            fiche.SurvolerPoint(DansLaCellule(maillee, absente));
            StringAssert.EndsWith("\nHabitants et faim : cellule absente du monde servi au tick 30", fiche.TexteAffiche);
            Assert.AreEqual(absente, fiche.Survolee?.CellId);
        }

        [Test] public void Hors_des_cellules_la_fiche_se_cache() {
            Servir(); Poser();
            fiche.SurvolerPoint(objet.transform.TransformPoint(new Vector3(1e6f, 0, 1e6f)));
            Assert.IsNull(fiche.Survolee); Assert.IsNull(fiche.TexteAffiche, "la fiche reste affichée hors de la carte");
            fiche.SurvolerPoint(DansLaCellule(MaillageDeCarte.Mailler(Lue()), METZ)); Assert.IsNotNull(fiche.TexteAffiche);
            fiche.Quitter(); Assert.IsNull(fiche.TexteAffiche, "la fiche reste affichée après le survol");
        }

        [Test] public void Sans_monde_la_fiche_le_dit_et_garde_la_carte() {
            statutMonde = 500; Servir(); Poser();
            fiche.SurvolerPoint(DansLaCellule(MaillageDeCarte.Mailler(Lue()), METZ));
            StringAssert.StartsWith("Cellule 10437 · Metz\nPuissance : ", fiche.TexteAffiche);
            StringAssert.Contains("\nHabitants et faim : " + CarteDessinee.MESSAGE_ABSENCE + " (", fiche.TexteAffiche);
            Assert.IsNull(fiche.MondeLu);
        }
    }
}
