using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using Forge.Pont;
using NUnit.Framework;
using UnityEngine;
using Object = UnityEngine.Object;

namespace Forge.Interface.Tests
{
    // La carte de la guerre sur trois terres carrées de 10 km côte à côte (10, 20, 30, d'ouest en est), lues par des lectures dictées.
    // La carte témoin est posée par `Montrer` : ses km locaux partent du centre des trois terres, (15 km, 5 km), et les
    // terres, sans puissance servie, y prennent la teinte des cellules sans puissance.
    public sealed class CarteDeLaGuerreTests
    {
        const string A = "pays-a", B = "pays-b";
        GameObject racine, toile; CarteDessinee carte; CarteDeLaGuerre guerre; CalquesCarte calques; double horloge;

        [SetUp] public void Ouvrir()
        {
            horloge = 0;
            racine = new GameObject("Carte de la guerre témoin", typeof(CarteDessinee)); carte = racine.GetComponent<CarteDessinee>();
            var camera = new GameObject("Caméra témoin").AddComponent<Camera>(); camera.transform.SetParent(racine.transform, false);
            camera.orthographic = true; camera.orthographicSize = 20; camera.transform.SetPositionAndRotation(new Vector3(0, 100, 0), Quaternion.Euler(90, 0, 0)); carte.camera = camera;
            carte.Montrer(new CarteLue(3, new[] { Carre(10, 0), Carre(20, 10000), Carre(30, 20000) }));
            Assert.That(carte.CellulesPosees, Is.EqualTo(3), "la carte témoin n'est pas posée");
            toile = new GameObject("Toile témoin", typeof(Canvas));
            calques = racine.AddComponent<CalquesCarte>(); calques.Initialiser(carte, toile.transform, () => null, () => null);
            guerre = racine.AddComponent<CarteDeLaGuerre>(); guerre.Installer(); calques.Brancher(null, null, guerre);
        }
        [TearDown] public void Fermer() { carte.Arreter(); Object.DestroyImmediate(racine); Object.DestroyImmediate(toile); }

        static CelluleDeCarte Carre(long id, double x)
        {
            var anneau = new[] { new PointCarte(x, 0), new PointCarte(x + 10000, 0), new PointCarte(x + 10000, 10000), new PointCarte(x, 10000), new PointCarte(x, 0) };
            return new CelluleDeCarte(id, new[] { new PolygoneDeCarte(anneau, new IEnumerable<PointCarte>[0]) }, null, null, new VilleDeCarte[0]);
        }
        // Les pays des terres 10, 20 et 30, nommés « Avalon » et « Brume » ; le maître de chaque terre est « m » suivi de son numéro.
        static TerresDeLaCarte Terres(string p10, string p20, string p30, long jour = 6) => new TerresDeLaCarte(jour - 1, new DateDuMonde(1400, jour),
            new[] { new PaysDeLaCarte(A, "Avalon"), new PaysDeLaCarte(B, "Brume") }.Where(p => new[] { p10, p20, p30 }.Contains(p.Id)),
            new[] { new TerreLue(10, "m10", p10), new TerreLue(20, "m20", p20), new TerreLue(30, "m30", p30) });
        static GuerresLues Guerres(params ArmeeLue[] armees) => new GuerresLues(5, new DateDuMonde(1400, 6), new GuerreLue[0], armees, new PriseLue[0], 0);
        static ArmeeLue Armee(long? siege, params PointCarte[] etapes) => new ArmeeLue(0, "m20", 20, 0, 1200, 500, siege,
            siege == null ? new LieuDuPays(30, 0) : null, siege == null ? new[] { 30L } : new long[0], new PointCarte(15000, 5000), etapes);

        void Servir(Func<Lecture<TerresDeLaCarte>> terres, Func<Lecture<GuerresLues>> guerres = null)
        {
            guerre.LecteurTerres = terres; guerre.LecteurGuerres = guerres ?? (() => Lecture<GuerresLues>.De(Guerres()));
            guerre.Pas(horloge); var fin = DateTime.UtcNow.AddSeconds(10); while (guerre.LectureEnVol && DateTime.UtcNow < fin) System.Threading.Thread.Sleep(5);
            Assert.That(guerre.LectureEnVol, Is.False, "lecture encore en vol"); guerre.Pas(horloge); horloge += CarteDeLaGuerre.PERIODE_S;
        }
        void Servir(TerresDeLaCarte terres, params ArmeeLue[] armees) => Servir(() => Lecture<TerresDeLaCarte>.De(terres), () => Lecture<GuerresLues>.De(Guerres(armees)));
        void Peindre() => typeof(CalquesCarte).GetMethod("LateUpdate", BindingFlags.Instance | BindingFlags.NonPublic).Invoke(calques, null);
        Color32 Teinte(long id) => carte.TeinteDe(id).Value;
        static Color32 Depart => SocleInterface.Pigment(MaillageDeCarte.CouleurSansPuissance);
        static Color32 DuPays(string pays) => CalquesCarte.Teinte(ModeDeCarte.Puissances, false, CarteDeLaGuerre.CouleurDuPays(pays), 0f);

        [Test] public void La_terre_prend_la_teinte_de_son_pays_servi_et_la_change_avec_lui()
        {
            Peindre();
            Assert.That(new[] { Teinte(10), Teinte(20), Teinte(30) }, Is.All.EqualTo(Depart), "sans terres lues : la puissance relevée au dessin");
            var terrain = racine.transform.Find(CarteDessinee.TERRAIN).GetComponent<MeshRenderer>(); Material matiere = terrain.sharedMaterial;
            Servir(Terres(A, A, B)); Peindre();
            Assert.That((Teinte(10), Teinte(20), Teinte(30)), Is.EqualTo((DuPays(A), DuPays(A), DuPays(B))));
            Assert.That(DuPays(A), Is.Not.EqualTo(DuPays(B)), "deux pays de même teinte : échantillon vide");
            Assert.That(calques.Legende.text, Is.EqualTo("Pays au jour 6 de 1400 · Rouge : territoire conservé"));
            Assert.That(TexteDuMonde.Interdit(calques.Legende.text) ?? TexteDuMonde.SansUnite(calques.Legende.text), Is.Null);
            // La terre 30 est prise par le pays A : elle seule change de teinte.
            int version = guerre.Version; Servir(Terres(A, A, A, 7)); Assert.That(guerre.Version, Is.EqualTo(version + 1)); Peindre();
            Assert.That((Teinte(10), Teinte(20), Teinte(30)), Is.EqualTo((DuPays(A), DuPays(A), DuPays(A))));
            Assert.That(terrain.sharedMaterial, Is.SameAs(matiere), "une terre prise ne change pas le matériau du terrain"); Assert.That(racine.GetComponentsInChildren<MeshFilter>(true).Count(f => f.name == CarteDessinee.TERRAIN), Is.EqualTo(1));
            Assert.That(calques.Legende.text, Does.StartWith("Pays au jour 7 de 1400"));
            // Contre-épreuve : les mêmes pays relus ne recolorent rien.
            Servir(Terres(A, A, A, 8)); Assert.That(guerre.Version, Is.EqualTo(version + 1), "mêmes pays : pas de nouvelle version");
        }

        [Test] public void Une_frontiere_entre_deux_pays_aucune_dans_un_meme_pays()
        {
            float loin = TerrainDeCarte.PORTEE_DES_FRONTIERES_KM;
            Servir(Terres(A, A, B)); Peindre();
            // Le côté commun de 20 et 30 (x = 5), compté depuis chacune des deux ; le côté commun de 10 et 20 est dans le même pays.
            // Le terrain trace la frontière : la distance qu'il en donne est celle de ce côté, lue au centre d'un texel d'un km.
            Assert.That(guerre.CotesDeFrontiere, Is.EqualTo(2)); Assert.That((carte.PaysDe(10), carte.PaysDe(20), carte.PaysDe(30)), Is.EqualTo((A, A, B)));
            Assert.That(carte.DistanceALaFrontiere(4.5f, .5f), Is.EqualTo(.5f).Within(.1f)); Assert.That(carte.DistanceALaFrontiere(5.5f, .5f), Is.EqualTo(.5f).Within(.1f));
            Assert.That(carte.DistanceALaFrontiere(-4.5f, .5f), Is.EqualTo(9.5f).Within(.1f), "une frontière sur le côté de 10 et 20, dans le même pays");
            Servir(Terres(A, A, A)); Peindre(); Assert.That(guerre.CotesDeFrontiere, Is.Zero, "contre-épreuve : un seul pays, aucune frontière"); Assert.That(carte.DistanceALaFrontiere(4.5f, .5f), Is.EqualTo(loin));
            Servir(Terres(A, B, B)); Peindre(); Assert.That(guerre.CotesDeFrontiere, Is.EqualTo(2));
            Assert.That(carte.DistanceALaFrontiere(-4.5f, .5f), Is.EqualTo(.5f).Within(.1f), "la frontière n'a pas suivi la terre prise"); Assert.That(carte.DistanceALaFrontiere(-5.5f, .5f), Is.EqualTo(.5f).Within(.1f));
            Assert.That(carte.DistanceALaFrontiere(4.5f, .5f), Is.EqualTo(9.5f).Within(.1f), "l'ancienne frontière est restée");
            Assert.That(racine.transform.Find("Frontières des pays"), Is.Null, "la guerre pose encore un tracé de frontières au-dessus du terrain");
        }

        [Test] public void Un_nom_par_pays_sur_sa_terre_la_plus_centrale()
        {
            Servir(Terres(A, A, B)); var noms = guerre.NomsDesPays;
            Assert.That(noms.Select(n => n.text), Is.EquivalentTo(new[] { "Avalon", "Brume" }));
            var avalon = noms.Single(n => n.text == "Avalon").transform.localPosition; var brume = noms.Single(n => n.text == "Brume").transform.localPosition;
            Assert.That((avalon - new Vector3(-10, CarteDeLaGuerre.HAUTEUR_NOM, 0)).magnitude < 1e-3f && (brume - new Vector3(10, CarteDeLaGuerre.HAUTEUR_NOM, 0)).magnitude < 1e-3f, Is.True, avalon + " / " + brume);
            Assert.That(noms.All(n => n.font == SocleInterface.Police(titre: true)), Is.True, "les noms ne sont pas dans la police du socle");
            Servir(Terres(A, A, A)); Assert.That(guerre.NomsDesPays.Select(n => n.text), Is.EqualTo(new[] { "Avalon" }), "le pays qui n'a plus de terre perd son nom");
            Assert.That(guerre.NomsDesPays.Single().transform.localPosition.x, Is.EqualTo(0f).Within(1e-3f));
        }

        [Test] public void Une_armee_dessinee_avec_son_nombre_et_sa_route_puis_retiree()
        {
            Servir(Terres(A, A, B), Armee(null, new PointCarte(25000, 5000)));
            var objet = racine.transform.Find(CarteDeLaGuerre.ARMEES + "/Armée 0"); Assert.That(objet, Is.Not.Null, "l'armée n'est pas dessinée");
            Assert.That((objet.localPosition - new Vector3(0, CarteDeLaGuerre.HAUTEUR_ARMEE, 0)).magnitude, Is.LessThan(1e-3f));
            Assert.That(objet.Find("Nombre").GetComponent<TextMesh>().text, Is.EqualTo("1 200 hommes"));
            Assert.That((Color32)objet.Find("Disque").GetComponent<MeshRenderer>().sharedMaterial.color, Is.EqualTo((Color32)CarteDeLaGuerre.CouleurDuPays(A)), "l'armée n'a pas la couleur de son pays");
            var route = objet.Find("Route").GetComponent<LineRenderer>(); Assert.That(route.positionCount, Is.EqualTo(2));
            Assert.That((objet.localPosition + route.GetPosition(1) - new Vector3(10, CarteDeLaGuerre.HAUTEUR_ROUTE, 0)).magnitude, Is.LessThan(1e-3f), "la route ne va pas à l'étape servie");
            Assert.That(guerre.TexteLegende, Does.Contain("\nAvalon : 1 200 hommes, en marche"));
            Assert.That(TexteDuMonde.Interdit(guerre.TexteLegende, A, B, "m20") ?? TexteDuMonde.SansUnite(guerre.TexteLegende), Is.Null, guerre.TexteLegende);
            Assert.That(objet.GetComponentsInChildren<Collider>(true), Is.Empty);
            // L'espacement des noms ne cache jamais le nombre d'une armée.
            Peindre(); objet.Find("Nombre").GetComponent<MeshRenderer>().enabled = false; Peindre(); Assert.That(objet.Find("Nombre").GetComponent<MeshRenderer>().enabled, Is.True);
            Servir(Terres(A, A, B), Armee(30)); objet = racine.transform.Find(CarteDeLaGuerre.ARMEES + "/Armée 0");
            Assert.That(objet.Find("Nombre").GetComponent<TextMesh>().text, Is.EqualTo("1 200 hommes · siège")); Assert.That(objet.Find("Route").GetComponent<LineRenderer>().positionCount, Is.Zero);
            Assert.That(guerre.NombresDesArmees, Has.Count.EqualTo(1));
            Servir(Terres(A, A, B)); Assert.That(racine.transform.Find(CarteDeLaGuerre.ARMEES).childCount, Is.Zero, "l'armée qui n'est plus servie reste dessinée"); Assert.That(guerre.NombresDesArmees, Is.Empty);
        }

        [Test] public void Une_lecture_absente_se_dit_et_rend_les_couleurs_du_depart()
        {
            Servir(Terres(A, A, B)); Peindre(); Assert.That(Teinte(30), Is.EqualTo(DuPays(B))); int version = guerre.Version;
            Assert.That(carte.PaysDe(30), Is.EqualTo(B)); Assert.That(carte.DistanceALaFrontiere(5.5f, .5f), Is.EqualTo(.5f).Within(.1f));
            Servir(() => Lecture<TerresDeLaCarte>.Absent("service coupé"), () => Lecture<GuerresLues>.Absent("délai dépassé")); Peindre();
            Assert.That(guerre.Version, Is.EqualTo(version + 1)); Assert.That(guerre.CouleurDe(30), Is.Null); Assert.That(Teinte(30), Is.EqualTo(Depart));
            // Les terres témoin n'ont pas de puissance servie : au départ elles ne sont à aucun pays, et rien ne les sépare.
            Assert.That(carte.PaysDe(30), Is.Null, "sans pays lus, la terre garde un pays servi"); Assert.That(carte.DistanceALaFrontiere(5.5f, .5f), Is.EqualTo(TerrainDeCarte.PORTEE_DES_FRONTIERES_KM), "sans pays lus, une frontière reste tracée");
            Assert.That(guerre.TexteLegende, Does.Contain("\nPays non lus : service coupé").And.Contain("\nArmées non lues : délai dépassé"));
            Assert.That(guerre.CotesDeFrontiere, Is.Zero); Assert.That(guerre.NomsDesPays, Is.Empty);
            Servir(() => throw new InvalidOperationException("lecteur en panne")); Assert.That(guerre.AbsenceDesTerres, Is.EqualTo("terres : lecteur en panne"));
        }
    }
}
