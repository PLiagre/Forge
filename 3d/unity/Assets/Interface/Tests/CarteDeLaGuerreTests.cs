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
        GameObject racine, toile; CarteDessinee carte; CarteDeLaGuerre guerre; CalquesCarte calques; double horloge; RenderTexture ecran;

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
        [TearDown] public void Fermer() { carte.camera.targetTexture = null; carte.Arreter(); Object.DestroyImmediate(racine); Object.DestroyImmediate(toile); if (ecran != null) Object.DestroyImmediate(ecran); ecran = null; }

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
        // La caméra témoin montre `demi` km de part et d'autre du centre sur un écran de 900 pixels de haut, et les noms s'y règlent.
        const int ECRAN_PX = 900;
        void Voir(float demi)
        {
            if (ecran == null) { ecran = new RenderTexture(1600, ECRAN_PX, 16); carte.camera.targetTexture = ecran; }
            carte.camera.orthographicSize = demi; guerre.SuivreLaVue();
        }
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

        // Un nom n'est plus un texte droit posé au centre d'une terre : il est couché sur le grand axe du territoire de
        // son pays, à la taille de son étendue. Le cas juge donc son tracé, son corps et ses lettres, plus la place d'un texte.
        [Test] public void Un_nom_par_pays_couche_sur_sa_terre_a_la_taille_de_son_etendue()
        {
            Servir(Terres(A, A, B)); var noms = guerre.NomsDesPays;
            Assert.That(noms.Select(n => n.Texte), Is.EquivalentTo(new[] { "Avalon", "Brume" }));
            NomCourbe avalon = noms.Single(n => n.Texte == "Avalon"), brume = noms.Single(n => n.Texte == "Brume");
            Assert.That((avalon.Pays, brume.Pays, avalon.Ecrit), Is.EqualTo((A, B, "AVALON")));
            // Avalon tient les terres 10 et 20 (x de -15 à 5 km), Brume la terre 30 (x de 5 à 15 km).
            Assert.That((avalon.Trace.Centre - new Vector2(-5, 0)).magnitude < .1f && (brume.Trace.Centre - new Vector2(10, 0)).magnitude < .1f, Is.True, avalon.Trace.Centre + " / " + brume.Trace.Centre);
            Assert.That(avalon.Trace.Axe.x, Is.EqualTo(1f).Within(1e-3f), "le nom n'est pas couché sur le grand axe de ses deux terres");
            Assert.That(avalon.Corps, Is.GreaterThan(1.3f * brume.Corps), "le nom du pays le plus étendu n'est pas écrit plus grand");
            Assert.That(guerre.Ecriture.Police, Is.SameAs(SocleInterface.Police(titre: true)), "les noms ne sont pas dans la police du socle");
            Color encre = SocleInterface.Couleur("encre"); encre.a = NomsCourbes.FORCE;
            Assert.That((Color32)guerre.Ecriture.Encre.GetColor("_Teinte"), Is.EqualTo((Color32)encre), "les noms ne sont pas à l'encre du socle");
            Assert.That((Color32)guerre.Ecriture.MatiereDuHalo.GetColor("_Teinte"), Is.EqualTo((Color32)SocleInterface.Couleur("papier")), "le halo des noms n'est pas au papier du socle");
            // Vus d'assez près pour se lire : un carré par lettre, tous sur la terre du pays, juste au-dessus du terrain.
            Voir(30f);
            Assert.That((avalon.Opacite, brume.Opacite), Is.EqualTo((1f, 1f))); Assert.That(avalon.Rendu.enabled && brume.Rendu.enabled, Is.True);
            Assert.That((avalon.Maillage.vertexCount, brume.Maillage.vertexCount), Is.EqualTo((4 * 6, 4 * 5)), "un carré par lettre");
            Bounds boite = avalon.Maillage.bounds;
            Assert.That(boite.min.x >= -15f && boite.max.x <= 5f && boite.min.z >= -5f && boite.max.z <= 5f, Is.True, "le nom déborde de sa terre : " + boite);
            Assert.That((boite.min.y, boite.max.y), Is.EqualTo((NomsCourbes.HAUTEUR, NomsCourbes.HAUTEUR)));
            Assert.That(avalon.Maillage.colors32.All(c => c.a == 255), Is.True, "un nom lisible n'est pas à pleine encre");
            // Le halo d'abord, l'encre ensuite, sur le même maillage ; deux noms partagent leurs matériaux.
            Assert.That(avalon.Rendu.sharedMaterials, Is.EqualTo(new[] { guerre.Ecriture.MatiereDuHalo, guerre.Ecriture.Encre })); Assert.That(brume.Rendu.sharedMaterials, Is.EqualTo(avalon.Rendu.sharedMaterials));
            Assert.That(guerre.Ecriture.MatiereDuHalo.renderQueue, Is.LessThan(guerre.Ecriture.Encre.renderQueue), "le halo se dessine après l'encre");
            Assert.That((avalon.Maillage.subMeshCount, guerre.Ecriture.MatiereDuHalo.GetFloat("_Halo"), guerre.Ecriture.Encre.GetFloat("_Halo")), Is.EqualTo((2, 1f, 0f)));
            Assert.That(avalon.Maillage.GetTriangles(0), Is.EqualTo(avalon.Maillage.GetTriangles(1)), "le halo et l'encre ne dessinent pas les mêmes carrés");
            // La terre 30 est prise par Avalon : Brume perd son nom, celui d'Avalon s'étend sur les trois terres et grandit.
            float avant = avalon.Corps; Servir(Terres(A, A, A)); Voir(30f);
            Assert.That(guerre.NomsDesPays.Select(n => n.Texte), Is.EqualTo(new[] { "Avalon" }), "le pays qui n'a plus de terre garde son nom");
            NomCourbe etendu = guerre.NomsDesPays.Single();
            Assert.That(etendu.Trace.Centre.x, Is.EqualTo(0f).Within(.1f), "le nom n'a pas suivi la conquête"); Assert.That(etendu.Corps, Is.GreaterThan(1.1f * avant), "le nom n'a pas grandi avec le pays");
            Assert.That(etendu.Maillage.bounds.max.x, Is.GreaterThan(5f), "le nom ne s'étend pas sur la terre prise");
            Assert.That(racine.GetComponentsInChildren<MeshFilter>(true).Count(f => f.name.StartsWith("Pays ")), Is.EqualTo(1), "un nom d'avant reste dessiné");
            // Contre-épreuve : les mêmes pays relus ne récrivent rien.
            Servir(Terres(A, A, A, 8)); Assert.That(guerre.NomsDesPays.Single(), Is.SameAs(etendu), "mêmes pays : le nom est récrit");
        }

        [Test] public void Un_nom_se_cache_de_trop_loin_et_s_efface_de_trop_pres()
        {
            float lisible = NomsCourbes.LISIBLE_PX, proche = NomsCourbes.PROCHE * ECRAN_PX, disparu = NomsCourbes.DISPARU * ECRAN_PX;
            Assert.That(lisible, Is.LessThan(proche), "échantillon vide : aucune taille où un nom se lit");
            Assert.That(NomsCourbes.Opacite(lisible - NomsCourbes.FONDU_PX, ECRAN_PX), Is.Zero, "un nom trop petit pour se lire se montre");
            Assert.That(NomsCourbes.Opacite(lisible, ECRAN_PX), Is.EqualTo(1f)); Assert.That(NomsCourbes.Opacite(proche, ECRAN_PX), Is.EqualTo(1f), "un nom lisible n'est pas à pleine encre");
            Assert.That(NomsCourbes.Opacite((proche + disparu) / 2f, ECRAN_PX), Is.EqualTo(.5f).Within(.01f)); Assert.That(NomsCourbes.Opacite(disparu, ECRAN_PX), Is.Zero, "un nom qui remplit la vue ne s'efface pas");
            Assert.That((NomsCourbes.TaillePour(9f), NomsCourbes.TaillePour(33f), NomsCourbes.TaillePour(500f)), Is.EqualTo((12, 48, 128)));
            Servir(Terres(A, A, B)); NomCourbe avalon = guerre.NomsDesPays.Single(n => n.Texte == "Avalon");
            float PxPour(float demi) => avalon.Corps * ECRAN_PX / (2f * demi);
            // À mi-distance le nom se lit ; ses lettres sont tirées de la police à la taille de l'écran.
            Voir(25f); Assert.That(guerre.Ecriture.CorpsALEcran(carte.camera, avalon), Is.EqualTo(PxPour(25f)).Within(.5f));
            Assert.That((avalon.Opacite, avalon.Rendu.enabled, avalon.Taille), Is.EqualTo((1f, true, NomsCourbes.TaillePour(PxPour(25f)))));
            // De très loin il ne se lirait plus : il se cache. De très près il remplirait la vue : il s'efface.
            Voir(2000f); Assert.That(PxPour(2000f), Is.LessThan(lisible - NomsCourbes.FONDU_PX)); Assert.That((avalon.Opacite, avalon.Rendu.enabled), Is.EqualTo((0f, false)), "le nom illisible reste montré");
            Voir(4f); Assert.That(PxPour(4f), Is.GreaterThan(disparu)); Assert.That((avalon.Opacite, avalon.Rendu.enabled), Is.EqualTo((0f, false)), "le nom reste devant une vue rapprochée");
            // Entre les deux il pâlit, et son encre avec lui ; puis il revient quand la vue recule.
            float demi = avalon.Corps * ECRAN_PX / (proche + disparu); Voir(demi);
            Assert.That(avalon.Opacite, Is.EqualTo(.5f).Within(.02f)); Assert.That(avalon.Rendu.enabled, Is.True);
            Assert.That(avalon.Maillage.colors32.All(c => c.a == Mathf.RoundToInt(255f * avalon.Opacite)), Is.True, "l'encre ne pâlit pas avec le nom");
            Voir(60f); Assert.That((avalon.Opacite, avalon.Rendu.enabled, avalon.Taille), Is.EqualTo((1f, true, NomsCourbes.TaillePour(PxPour(60f)))), "le nom ne revient pas quand la vue recule");
            Assert.That(NomsCourbes.TaillePour(PxPour(60f)), Is.LessThan(NomsCourbes.TaillePour(PxPour(25f))), "échantillon vide : la même taille de lettres aux deux distances");
            Assert.That(avalon.Maillage.vertexCount, Is.EqualTo(4 * 6));
            // Le halo est fort sous un petit nom, léger sous un grand, et suit la vue comme l'opacité.
            Assert.That((NomsCourbes.ForceDuHalo(NomsCourbes.PETIT_PX), NomsCourbes.ForceDuHalo(NomsCourbes.GRAND_PX)), Is.EqualTo((NomsCourbes.HALO_PETIT, NomsCourbes.HALO_GRAND)));
            Assert.That(avalon.Halo, Is.EqualTo(NomsCourbes.ForceDuHalo(PxPour(60f))).Within(.01f)); Assert.That(avalon.Maillage.colors32.All(c => c.r == Mathf.RoundToInt(255f * avalon.Halo)), Is.True, "le halo ne suit pas la vue");
        }

        // La police est dynamique : quand son atlas est refait, les lettres y changent de place, et un nom qui garderait
        // ses anciens carrés montrerait des morceaux d'autres lettres.
        [Test] public void Les_noms_se_remaillent_quand_l_atlas_de_la_police_est_refait()
        {
            Servir(Terres(A, A, B)); NomCourbe avalon = guerre.NomsDesPays.Single(n => n.Texte == "Avalon"); Voir(30f);
            Font police = guerre.Ecriture.Police; int refaits = 0; Action<Font> compter = f => { if (f == police) refaits++; };
            Vector2 Milieu(int lettre) { var uv = new List<Vector2>(); avalon.Maillage.GetUVs(0, uv); return (uv[4 * lettre] + uv[4 * lettre + 1] + uv[4 * lettre + 2] + uv[4 * lettre + 3]) / 4f; }
            Vector2 avant = Milieu(0);
            Font.textureRebuilt += compter;
            try
            {
                // Des centaines de lettres jamais demandées, en grand : l'atlas ne peut les loger sans se refaire.
                var lettres = new System.Text.StringBuilder(); for (char c = (char)0x100; c < 0x100 + 400; c++) lettres.Append(c);
                for (int taille = 150; taille <= 500 && refaits == 0; taille += 50) police.RequestCharactersInTexture(lettres.ToString(), taille);
            }
            finally { Font.textureRebuilt -= compter; }
            Assert.That(refaits, Is.GreaterThan(0), "échantillon vide : l'atlas de la police n'a pas été refait");
            guerre.SuivreLaVue();
            Assert.That(guerre.Ecriture.Encre.mainTexture, Is.SameAs(police.material.mainTexture)); Assert.That(guerre.Ecriture.MatiereDuHalo.mainTexture, Is.SameAs(police.material.mainTexture));
            Assert.That(avalon.Maillage.vertexCount, Is.EqualTo(4 * 6), "une lettre s'est perdue quand l'atlas a été refait");
            for (int i = 0; i < 6; i++)
            {
                Assert.That(police.GetCharacterInfo(avalon.Ecrit[i], out CharacterInfo lettre, avalon.Taille), Is.True, "la lettre " + avalon.Ecrit[i] + " n'est plus dans l'atlas");
                Assert.That((Milieu(i) - (lettre.uvBottomLeft + lettre.uvTopRight) / 2f).magnitude, Is.LessThan(1e-4f), "la lettre " + avalon.Ecrit[i] + " ne lit pas sa place dans l'atlas refait");
            }
            Assert.That((Milieu(0) - avant).magnitude, Is.GreaterThan(1e-4f), "échantillon vide : la première lettre n'a pas changé de place dans l'atlas");
        }

        // Un nom de pays ne passe plus par l'espacement des étiquettes : chacune de ses lettres y réserve sa place.
        [Test] public void Un_nom_de_ville_ne_s_ecrit_pas_sur_les_lettres_d_un_pays()
        {
            Servir(Terres(A, A, B)); NomCourbe avalon = guerre.NomsDesPays.Single(n => n.Texte == "Avalon"); Voir(30f);
            // Une ville sur la deuxième lettre d'Avalon, une autre au nord de la terre, loin de toute lettre.
            Vector2 lettre = avalon.Compose.Lettres[1].Point;
            MeshRenderer Ville(string nom, Vector3 ici) { var t = new GameObject(nom).AddComponent<TextMesh>(); t.text = nom; t.transform.SetParent(racine.transform, false); t.transform.localPosition = ici; return t.GetComponent<MeshRenderer>(); }
            MeshRenderer dessus = Ville("Ville sur la lettre", new Vector3(lettre.x, CarteDessinee.HAUTEUR_NOM, lettre.y)), ailleurs = Ville("Ville au nord", new Vector3(lettre.x, CarteDessinee.HAUTEUR_NOM, 4.5f));
            var places = new List<Rect>(); guerre.Ecriture.Reserver(carte.camera, places);
            Assert.That(places, Has.Count.EqualTo(6 + 5), "une place par lettre des deux noms lisibles");
            Vector2 ecranDeLaLettre = carte.camera.WorldToScreenPoint(racine.transform.TransformPoint(new Vector3(lettre.x, NomsCourbes.HAUTEUR, lettre.y)));
            Assert.That(places.Count(p => p.Contains(ecranDeLaLettre)), Is.EqualTo(1), "la place de la lettre n'est pas autour d'elle");
            Peindre(); Peindre(); // les étiquettes sont relevées au premier passage, espacées à partir du suivant
            Assert.That((dessus.enabled, ailleurs.enabled), Is.EqualTo((false, true)), "le nom de ville sur la lettre se montre, ou celui d'à côté se cache");
            // De près, le nom du pays s'efface : il ne réserve plus rien, et la ville revient.
            Voir(10f); Assert.That(avalon.Opacite, Is.Zero, "échantillon vide : le nom du pays ne s'est pas effacé"); places.Clear(); guerre.Ecriture.Reserver(carte.camera, places);
            ecranDeLaLettre = carte.camera.WorldToScreenPoint(racine.transform.TransformPoint(new Vector3(lettre.x, NomsCourbes.HAUTEUR, lettre.y)));
            Assert.That(places, Has.Count.EqualTo(5), "seul le nom encore lisible, Brume, réserve ses lettres"); Assert.That(places.Any(p => p.Contains(ecranDeLaLettre)), Is.False, "un nom effacé réserve encore sa place");
            Peindre(); Assert.That(dessus.enabled, Is.True, "le nom de ville ne revient pas quand le nom du pays s'efface");
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
