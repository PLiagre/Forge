using System.Collections.Generic;
using System.Linq;
using Forge.Pont;
using Forge.Pont.Tests;
using NUnit.Framework;
using UnityEngine;

namespace Forge.Interface.Tests
{
    // Les noms des pays sur l'Europe entière relevée du vrai service, et les noms des villes qui se rangent autour d'eux.
    public sealed class CarteDeLaGuerreEuropeTests
    {
        EuropeDeCarte europe;
        [OneTimeSetUp] public void Poser() => europe = new EuropeDeCarte();
        [OneTimeTearDown] public void Fermer() => europe?.Dispose();
        static TerresDeLaCarte Terres => EuropeDeTest.TerresEurope;

        // Chaque pays qui tient une terre et que le monde nomme a son nom sur la carte, celui servi ; aucun nom de pays dessiné
        // n'est celui d'une dynastie : la maison d'un pays qui porte un autre nom qu'elle (« Luxembourg », « Valois »), quand
        // aucun pays servi ne porte ce nom (la Poméranie est un pays et le nom de la maison de l'Union de Kalmar).
        [Test] public void Chaque_pays_tenant_porte_son_nom_et_jamais_celui_d_une_maison()
        {
            var tenants = new HashSet<string>(Terres.Terres.Select(t => t.Pays).Where(p => p != null));
            var nommes = Terres.Pays.Where(p => tenants.Contains(p.Id) && p.Nom != null).ToList();
            Assert.That(nommes.Count, Is.GreaterThan(50), "échantillon vide : trop peu de pays tenants nommés");
            var ecrits = europe.Guerre.NomsDesPays.ToDictionary(n => n.Pays);
            foreach (var p in nommes) Assert.That(ecrits.TryGetValue(p.Id, out NomCourbe nom) ? nom.Texte : null, Is.EqualTo(p.Nom), p.Id + " n'a pas son nom servi sur la carte");
            Assert.That(ecrits.Keys.All(tenants.Contains), Is.True, "un pays sans terre a un nom sur la carte");
            var pays = new HashSet<string>(Terres.Pays.Select(p => p.Nom).Where(n => n != null));
            var dynasties = new HashSet<string>(Terres.Pays.Where(p => p.Maison?.Nom != null && p.Maison.Nom != p.Nom && !pays.Contains(p.Maison.Nom)).Select(p => p.Maison.Nom));
            Assert.That(dynasties, Does.Contain("Luxembourg").And.Contain("Valois"), "échantillon vide : les dynasties de la Bohême et de la France ne sont pas servies");
            var fautifs = europe.Guerre.NomsDesPays.Where(n => dynasties.Contains(n.Texte)).Select(n => n.Pays + " « " + n.Texte + " »").ToList();
            Assert.That(fautifs, Is.Empty, "un nom de dynastie est dessiné comme nom de pays");
            // La dynastie s'écrit en petit sous son pays, jamais en grand.
            NomCourbe boheme = europe.Guerre.NomsDesPays.Single(n => n.Texte == "Bohême");
            Assert.That(boheme.Maison?.Texte, Is.EqualTo(Terres.MaisonDuPays(boheme.Pays).Nom)); Assert.That(boheme.Maison.Corps, Is.LessThan(boheme.Corps));
        }

        // Un vassal servi qui tient une terre écrit sous son nom « vassal de » son suzerain, tel que le monde le nomme ; un pays sans suzerain n'écrit rien.
        // De loin la ligne est trop petite pour se lire ; de près, là où le nom du pays se lit encore, elle se lit.
        [Test] public void Un_vassal_ecrit_sous_son_nom_de_qui_il_releve_et_seulement_de_pres()
        {
            var tenants = new HashSet<string>(Terres.Terres.Select(t => t.Pays).Where(p => p != null));
            var ecrits = europe.Guerre.NomsDesPays.ToDictionary(n => n.Pays);
            var vassaux = Terres.Pays.Where(p => p.Suzerain != null && tenants.Contains(p.Id) && ecrits.ContainsKey(p.Id)).ToList();
            Assert.That(vassaux.Count, Is.GreaterThan(0), "échantillon vide : aucun vassal servi ne tient une terre et n'a de nom dessiné");
            foreach (var p in vassaux)
            {
                string attendu = NomsCourbes.Vassalite(Terres.NomDuPays(p.Suzerain));
                Assert.That(ecrits[p.Id].Vassalite?.Texte, Is.EqualTo(attendu), p.Id + " n'écrit pas de quel pays il relève");
            }
            Assert.That(ecrits.Values.Where(n => Terres.SuzerainDe(n.Pays) == null && n.Vassalite != null).Select(n => n.Texte), Is.Empty, "un pays sans suzerain écrit une vassalité");
            Assert.That(europe.Guerre.NomsDesPays.Count(n => n.Vassalite != null), Is.EqualTo(vassaux.Count(p => NomsCourbes.Vassalite(Terres.NomDuPays(p.Suzerain)) != null)), "échantillon vide ou trop plein : le compte des vassalités écrites n'est pas celui des vassaux au suzerain nommé");
            NomCourbe guyenne = ecrits["puissance-42"], bourgogne = ecrits["puissance-40"], france = ecrits["puissance-3"];
            Assert.That((guyenne.Vassalite?.Texte, bourgogne.Vassalite?.Texte, france.Vassalite?.Texte), Is.EqualTo(("vassal d'Angleterre", "vassal de France", (string)null)));
            // De loin, la ligne est trop petite pour se lire ; de près, la Guyenne se lit encore et sa vassalité avec elle.
            europe.Voir(Vector2.zero, 1500f); Assert.That(guyenne.Vassalite.Opacite, Is.Zero, "la vassalité de la Guyenne se lit sur toute l'Europe"); Assert.That(guyenne.Vassalite.Rendu.enabled, Is.False);
            const float DEMI = 100f;
            europe.Voir(guyenne.Trace.Centre, DEMI);
            Assert.That(guyenne.Opacite, Is.GreaterThan(0f), "échantillon vide : le nom de la Guyenne ne se lit pas à " + DEMI + " km (" + guyenne.CorpsPx + " px)");
            Assert.That(guyenne.Vassalite.Opacite, Is.GreaterThan(0f), "la vassalité de la Guyenne ne se lit pas à " + DEMI + " km : " + guyenne.Vassalite.CorpsPx + " px, le nom " + guyenne.CorpsPx + " px, la maison " + guyenne.Maison?.CorpsPx + " px");
            Assert.That(guyenne.Vassalite.Rendu.enabled, Is.True);
        }

        // Le nom du pays du joueur se lit de la vue de l'Europe entière, où un pays aussi petit se cache : le Duché de Bar, joué, s'agrandit
        // jusqu'à un corps lisible ; sans joueur, il se cache comme les autres.
        [Test] public void Le_nom_du_pays_du_joueur_se_lit_sur_toute_l_Europe()
        {
            NomCourbe bar = europe.Guerre.NomsDesPays.Single(n => n.Pays == "seigneurie-1");
            try
            {
                europe.Voir(Vector2.zero, 1500f);
                Assert.That(bar.Opacite, Is.Zero, "échantillon vide : le Duché de Bar se lit sur toute l'Europe sans être joué (" + bar.CorpsPx + " px)");
                europe.Guerre.LecteurDuJoueur = () => "seigneurie-1"; Assert.That(europe.Guerre.PaysDuJoueur, Is.EqualTo("seigneurie-1"));
                europe.Voir(Vector2.zero, 1500f);
                Assert.That(bar.CorpsPx, Is.GreaterThanOrEqualTo(NomsCourbes.CORPS_DU_JOUEUR_PX - 0.5f), "le nom du joueur est trop petit pour se lire");
                Assert.That(bar.Opacite, Is.EqualTo(1f)); Assert.That(bar.Rendu.enabled && bar.Maillage.vertexCount > 0, Is.True, "le nom du joueur n'est pas dessiné");
                Assert.That(europe.Guerre.NomsDesPays.Where(n => n != bar && n.Agrandissement != 1f), Is.Empty, "un autre pays que celui du joueur s'agrandit");
            }
            finally { europe.Guerre.LecteurDuJoueur = null; europe.Voir(Vector2.zero, 1500f); }
            Assert.That(bar.Agrandissement, Is.EqualTo(1f), "le nom reste agrandi quand le joueur n'est plus ce pays");
        }

        // À toute distance, aucun nom de ville montré ne s'écrit sur une lettre d'un nom de pays ou de l'atlas lisible.
        [Test] public void Aucun_nom_de_ville_ne_s_ecrit_sur_un_nom_de_pays_lisible()
        {
            var vues = new[] { ("l'Europe", Vector2.zero, 1500f), ("la France", Centre("France"), 450f), ("l'Italie", Centre("Royaume de Naples", "Naples"), 350f), ("la Bohême", Centre("Bohême"), 250f) };
            int villes = 0, lettres = 0;
            foreach (var (ou, centre, demi) in vues)
            {
                europe.Voir(centre, demi);
                var pris = europe.LettresDesPays().Concat(europe.LettresDeLAtlas()).ToList(); var montrees = europe.Calques.PlacesDesVilles.ToList();
                villes += montrees.Count; lettres += pris.Count;
                var dePays = europe.LettresDesPays();
                foreach (Rect ville in montrees) Assert.That(pris.Any(l => l.Overlaps(ville)), Is.False, "sur " + ou + ", un nom de ville s'écrit sur la lettre d'un nom lisible : " + ville + (europe.Calques.PlacesDesCapitales.Contains(ville) ? " (une capitale)" : "") + (dePays.Any(l => l.Overlaps(ville)) ? " sur un pays" : " sur l'atlas : " + string.Join(", ", europe.Atlas.Noms.Where(n => { var ls = new List<Rect>(); europe.Atlas.Ecriture.Places(europe.Carte.camera, n, ls); return n.Opacite >= NomsCourbes.OPACITE_QUI_RESERVE && ls.Any(l => l.Overlaps(ville)); }).Select(n => n.Texte + " masqué " + n.Masque))));
            }
            Assert.That(villes, Is.GreaterThan(0), "échantillon vide : aucun nom de ville montré"); Assert.That(lettres, Is.GreaterThan(0), "échantillon vide : aucun nom lisible");
        }

        // Le centre du nom d'un pays servi, d'après le premier nom trouvé.
        Vector2 Centre(params string[] noms) => europe.Guerre.NomsDesPays.First(n => noms.Contains(n.Texte)).Trace.Centre;
    }

    // Les noms des pays sur les Détroits relevés du vrai service, avec les vraies formes de leurs lieux (`FormesDeTest.TerrainDetroits`) et
    // les terres de l'Europe : dans la cellule de Constantinople, des lieux byzantins côtoient des lieux ottomans.
    public sealed class NomsDesDetroitsTests
    {
        GameObject racine; CarteDessinee carte; CarteDeLaGuerre guerre;
        [OneTimeSetUp] public void Poser()
        {
            racine = new GameObject("Détroits témoins", typeof(CarteDessinee)); carte = racine.GetComponent<CarteDessinee>();
            var camera = new GameObject("Caméra témoin").AddComponent<Camera>(); camera.transform.SetParent(racine.transform, false);
            camera.orthographic = true; camera.nearClipPlane = 1f; camera.farClipPlane = 20000f; camera.transform.SetPositionAndRotation(new Vector3(0, 5000, 0), Quaternion.Euler(90, 0, 0)); carte.camera = camera;
            carte.Montrer(FormesDeTest.CarteDetroits, FormesDeTest.FormesDetroits);
            Assert.That(carte.CellulesPosees, Is.EqualTo(FormesDeTest.CarteDetroits.Cellules.Count), "les Détroits ne sont pas posés");
            guerre = racine.AddComponent<CarteDeLaGuerre>(); guerre.Installer();
            TerresDeLaCarte terres = EuropeDeTest.TerresEurope;
            guerre.LecteurTerres = () => Lecture<TerresDeLaCarte>.De(terres);
            guerre.LecteurGuerres = () => Lecture<GuerresLues>.De(new GuerresLues(terres.Tick, terres.Date, new GuerreLue[0], new ArmeeLue[0], new PriseLue[0], 0));
            double t = 0; var fin = System.DateTime.UtcNow.AddSeconds(60);
            while (System.DateTime.UtcNow < fin && (guerre.Couleurs == null || guerre.LectureEnVol || guerre.NomsDesPays.Count == 0)) { guerre.Pas(t); t += CarteDeLaGuerre.PERIODE_S; System.Threading.Thread.Sleep(20); }
            Assert.That(guerre.Couleurs != null && guerre.NomsDesPays.Count > 0, Is.True, "les pays des Détroits ne sont pas lus et nommés : " + guerre.AbsenceDesTerres);
        }
        [OneTimeTearDown] public void Fermer() { if (carte != null) { carte.camera.targetTexture = null; carte.Arreter(); } Object.DestroyImmediate(racine); }

        // Le pays du lieu sous un point de la carte, comme les couleurs le peignent ; null sur la mer.
        string PaysSous(Vector2 p)
        {
            TerrainDeCarte terrain = carte.Terrain; ushort n = terrain.LieuEn(p.x, p.y); if (n == 0) return null;
            return guerre.Terres.PaysDuLieu(carte.Lue.Cellules[terrain.CelluleDuLieu(n - 1)].CellId, terrain.RangDuLieu(n - 1));
        }

        // Chaque lettre du nom d'un pays qui tombe sur la terre tombe sur un lieu de ce pays : Byzance ne s'écrit plus sur la Thrace ottomane,
        // ni les Ottomans sur les lieux de Constantinople. Les deux pays sont écrits, et chacun pose des lettres chez lui.
        [Test] public void Chaque_lettre_du_nom_d_un_pays_tombe_sur_un_lieu_de_ce_pays()
        {
            var ecrits = guerre.NomsDesPays.ToDictionary(n => n.Pays);
            Assert.That(ecrits.Keys, Does.Contain("puissance-25").And.Contain("puissance-26"), "échantillon vide : Byzance ou les Ottomans ne sont pas écrits sur les Détroits");
            foreach (NomCourbe nom in guerre.NomsDesPays)
            {
                int chezSoi = 0; var ailleurs = new List<string>();
                for (int i = 0; i < nom.Ecrit.Length; i++)
                {
                    if (char.IsWhiteSpace(nom.Ecrit[i])) continue;
                    string pays = PaysSous(nom.Compose.Lettres[i].Point); if (pays == null) continue;
                    if (pays == nom.Pays) chezSoi++; else ailleurs.Add("« " + nom.Ecrit[i] + " » sur " + (guerre.Terres.NomDuPays(pays) ?? pays));
                }
                Assert.That(ailleurs, Is.Empty, nom.Texte + " s'écrit sur les lieux d'un autre pays");
                Assert.That(chezSoi, Is.GreaterThan(nom.Ecrit.Length / 2), nom.Texte + " ne pose presque aucune lettre sur ses lieux");
            }
        }
    }
}
