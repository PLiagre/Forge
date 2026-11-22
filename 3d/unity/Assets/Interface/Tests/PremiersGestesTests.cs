using System.Collections.Generic;
using System.Linq;
using Forge.Pont;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.UI;
using Object = UnityEngine.Object;

namespace Forge.Interface.Tests
{
    // L'encart des trois premiers gestes, dans le vrai cabinet : caché sans maison, une phrase par bouton, ses lignes faites d'après
    // ce que le monde sert, son état fermé gardé d'une carte à l'autre, et aucun recouvrement des panneaux voisins.
    public sealed class PremiersGestesTests
    {
        const string SCENE_SERVIE = "3d/unity/Assets/ForgeLocal3D/Desert/Scenes/Forge_Desert_Ville_ksar_des_sept_puits.unity";
        static readonly DateDuMonde Jour = new DateDuMonde(1400, 2);
        static readonly FicheJouable Zab = new FicheJouable("seigneurie-6", "Banou Mozni", "seigneurie", 4, new IdentiteDePays("seigneurie-6", "Émirat du Zab"),
            new[] { new IdentiteDePays("seigneurie-6", "Émirat du Zab") }, new SiegeJouable("Biskra", "Biskra", 10103), null, new VilleJouable(true, SCENE_SERVIE, null));
        static readonly FicheJouable Valois = new FicheJouable("grande-3", "Valois", "grande maison", 40, new IdentiteDePays("puissance-2", "France"),
            new[] { new IdentiteDePays("puissance-2", "France") }, new SiegeJouable("Paris", "Paris", 10200), null,
            new VilleJouable(false, null, "la ville de Paris n'est pas encore bâtie en 3D ; seule Biskra l'est"));

        GameObject racine; CabinetDeCarte cabinet; LecturePartie partie; PassageALaCapitale passage; readonly List<string> chargees = new List<string>();

        [SetUp] public void Ouvrir()
        {
            PremiersGestes.OublierLesFermetures(); PassageALaCapitale.PrendreCelluleRemise(string.Empty); chargees.Clear();
            Monter();
        }
        [TearDown] public void Fermer() { Demonter(); PremiersGestes.OublierLesFermetures(); }

        // Un cabinet neuf sur une partie neuve, comme après un aller-retour par la ville.
        void Monter()
        {
            racine = new GameObject("Carte de contrôle", typeof(CarteDessinee), typeof(HorlogeDeCarte), typeof(FicheDeCellule), typeof(ReperesDeDepart));
            passage = racine.AddComponent<PassageALaCapitale>(); passage.ChargerScene = nom => chargees.Add(nom);
            cabinet = racine.AddComponent<CabinetDeCarte>(); cabinet.Construire();
            partie = new LecturePartie(() => null, _ => null, () => null, _ => null); cabinet.Partie = partie;
        }
        void Demonter() { racine.GetComponent<CarteDessinee>().Arreter(); Object.DestroyImmediate(racine); }

        static void Poser(object cible, string nom, object valeur) => cible.GetType().GetProperty(nom).GetSetMethod(true).Invoke(cible, new[] { valeur });
        void Servir(string maison, params FicheJouable[] fiches)
        {
            Poser(partie, "Monde", Lecture<MondeAvecMaisonLu>.De(new MondeAvecMaisonLu(new MondeLu(1, Jour, 0, new CelluleDuMonde[0]), maison)));
            Poser(partie, "Jouables", fiches.Length == 0 ? null : Lecture<JouablesLus>.De(new JouablesLus(1, Jour, fiches)));
            cabinet.Afficher();
        }
        void Horloge(double joursParSeconde) { Poser(racine.GetComponent<HorlogeDeCarte>(), "Lue", new HorlogeLue(3, Jour, joursParSeconde)); cabinet.Afficher(); }
        void Armees(params string[] maisons)
        {
            Poser(racine.GetComponent<CarteDeLaGuerre>(), "Guerres", new GuerresLues(1, Jour, new GuerreLue[0],
                maisons.Select((m, i) => new ArmeeLue(i, m, 10, 0, 1200, 500, null, null, new long[0], new PointCarte(81000, 2000), new PointCarte[0])), new PriseLue[0], 0));
            cabinet.Afficher();
        }
        PremiersGestes Gestes => cabinet.Gestes;

        [Test] public void Sans_maison_l_encart_est_cache_puis_visible_avec_une_maison()
        {
            Assert.That(Gestes.Visible, Is.False, "visible avant toute lecture");
            Servir(null, Zab, Valois); Assert.That(Gestes.Visible, Is.False, "visible sans maison du joueur");
            Servir("seigneurie-6", Zab, Valois); Assert.That(Gestes.Visible, Is.True, "caché avec une maison servie");
            Assert.That(Gestes.Panneau.name, Is.EqualTo(PremiersGestes.TITRE));
        }

        [Test] public void Chaque_bouton_de_l_encart_dit_ce_qu_il_fait()
        {
            Servir("grande-3", Zab, Valois);
            var boutons = Gestes.Panneau.GetComponentsInChildren<Button>(true);
            CollectionAssert.AreEquivalent(new[] { Gestes.BoutonTemps, Gestes.BoutonVille, Gestes.BoutonArmee, Gestes.BoutonFermer }, boutons, "l'encart n'a pas ses quatre boutons");
            string[] sans = CabinetDeCarte.CommandesSansPhrase(Gestes.Panneau); Assert.That(sans, Is.Empty, "commandes sans phrase : " + string.Join(", ", sans));
            foreach (var texte in Gestes.Panneau.GetComponentsInChildren<Text>(true)) Assert.That(texte.supportRichText, Is.False, "texte à balises : " + texte.name);
        }

        [Test] public void Entrer_dans_la_ville_est_grise_pour_une_ville_non_batie_et_dit_la_raison_servie()
        {
            Servir("grande-3", Zab, Valois);
            Assert.That(Gestes.BoutonVille.interactable, Is.False);
            string raison = "La ville de Paris n'est pas encore bâtie en 3D ; seule Biskra l'est.";
            Assert.That(Gestes.BoutonVille.GetComponent<Infobulle>().Phrase, Is.EqualTo(raison));
            Assert.That(cabinet.Ville.Phrase, Is.EqualTo(raison), "la raison de l'encart n'est pas celle du bandeau");
            Gestes.BoutonVille.onClick.Invoke(); CollectionAssert.IsEmpty(chargees, "le bouton grisé a ouvert une ville");
        }

        [Test] public void Entrer_dans_la_ville_est_actif_pour_une_ville_batie_et_demande_la_scene_servie()
        {
            Servir("seigneurie-6", Zab, Valois);
            Assert.That(Gestes.BoutonVille.interactable, Is.True);
            Assert.That(Gestes.BoutonVille.GetComponent<Infobulle>().Phrase, Is.EqualTo("Ouvre Biskra, votre capitale."));
            Gestes.BoutonVille.onClick.Invoke();
            CollectionAssert.AreEqual(new[] { TerresAvecKit.Scenes["seigneurie-6"] }, chargees, "la scène demandée n'est pas celle du bandeau");
            Assert.That(PassageALaCapitale.PrendreCelluleRemise(TerresAvecKit.Scenes["seigneurie-6"]), Is.EqualTo(10103L), "la remise ne porte pas le siège servi");
            cabinet.Afficher(); Assert.That(Gestes.BoutonVille.interactable, Is.False, "l'encart reste actif après la descente, comme le bouton du bandeau");
            Gestes.BoutonVille.onClick.Invoke(); Assert.That(chargees.Count, Is.EqualTo(1), "la ville s'ouvre deux fois");
        }

        [Test] public void Lancer_le_temps_est_fait_quand_l_horloge_file_et_son_clic_appelle_l_action()
        {
            Servir("seigneurie-6", Zab);
            Assert.That(Gestes.BoutonTemps.interactable, Is.False, "actif sans horloge lue");
            Assert.That(Gestes.BoutonTemps.GetComponent<Infobulle>().Phrase, Is.EqualTo(PremiersGestes.HORLOGE_ATTENDUE), "le bouton grisé ne dit pas pourquoi");
            Horloge(0); Assert.That(Gestes.Faite(0), Is.False, "faite en pause"); Assert.That(Gestes.Texte(0), Is.EqualTo(PremiersGestes.TEMPS));
            Assert.That(Gestes.BoutonTemps.interactable, Is.True);
            Horloge(1.5); Assert.That(Gestes.Faite(0), Is.True, "pas faite alors que le temps file");
            Assert.That(Gestes.Texte(0), Is.EqualTo(PremiersGestes.TEMPS + PremiersGestes.FAIT), "la ligne faite ne le dit pas en mots");
            Assert.That(Gestes.BoutonTemps.interactable, Is.True, "le bouton d'une ligne faite est grisé");
            Horloge(0); Assert.That(Gestes.Faite(0), Is.False, "reste faite quand le temps s'arrête");
        }

        [Test] public void Le_clic_de_lancer_le_temps_bascule_l_horloge_du_cabinet()
        {
            Servir("seigneurie-6", Zab);
            Horloge(1.5); var demandee = typeof(HorlogeDeCarte).GetField("vitesseDemandee", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance);
            var horloge = racine.GetComponent<HorlogeDeCarte>(); Assert.That(demandee.GetValue(horloge), Is.Null, "une vitesse est demandée avant tout clic");
            Gestes.BoutonTemps.onClick.Invoke();
            Assert.That(demandee.GetValue(horloge), Is.EqualTo(0.0), "le clic n'a pas demandé la pause à l'horloge qui file");
        }

        [Test] public void Lever_une_armee_ouvre_le_feuillet_de_la_guerre_et_se_marque_faite_avec_une_armee_de_la_maison()
        {
            Servir("seigneurie-6", Zab); var feuillet = racine.GetComponent<DossierGuerre>().Feuillet;
            Assert.That(feuillet.Ouvert, Is.False); Assert.That(Gestes.Faite(2), Is.False, "faite sans guerres lues");
            Gestes.BoutonArmee.onClick.Invoke(); Assert.That(feuillet.Ouvert, Is.True, "le feuillet de la guerre ne s'ouvre pas");
            Gestes.BoutonArmee.onClick.Invoke(); Assert.That(feuillet.Ouvert, Is.True, "un second clic referme le feuillet");
            Armees(); Assert.That(Gestes.Faite(2), Is.False, "faite sans armée");
            Armees("grande-3"); Assert.That(Gestes.Faite(2), Is.False, "faite pour l'armée d'une autre maison");
            Armees("grande-3", "seigneurie-6"); Assert.That(Gestes.Faite(2), Is.True, "pas faite avec une armée de la maison");
            Assert.That(Gestes.Texte(2), Is.EqualTo(PremiersGestes.ARMEE + PremiersGestes.FAIT));
        }

        [Test] public void Ferme_l_encart_reste_ferme_apres_la_reconstruction_du_cabinet_pour_la_meme_maison()
        {
            Servir("seigneurie-6", Zab); Assert.That(Gestes.Visible, Is.True);
            Gestes.BoutonFermer.onClick.Invoke(); Assert.That(Gestes.Visible, Is.False, "« Fermer » ne cache pas l'encart");
            cabinet.Afficher(); Assert.That(Gestes.Visible, Is.False, "l'image suivante le rouvre");
            Demonter(); Monter(); Servir("seigneurie-6", Zab);
            Assert.That(Gestes.Visible, Is.False, "le cabinet reconstruit rouvre l'encart de la même maison");
            Demonter(); Monter(); Servir("grande-3", Zab, Valois);
            Assert.That(Gestes.Visible, Is.True, "une autre maison ne voit pas l'encart");
            PremiersGestes.OublierLesFermetures(); Demonter(); Monter(); Servir("seigneurie-6", Zab);
            Assert.That(Gestes.Visible, Is.True, "contre-épreuve : l'état fermé ne se vide pas");
        }

        static Rect Monde(RectTransform t) { var c = new Vector3[4]; t.GetWorldCorners(c); return Rect.MinMaxRect(c.Min(v => v.x), c.Min(v => v.y), c.Max(v => v.x), c.Max(v => v.y)); }
        [Test] public void L_encart_ne_recouvre_ni_les_feuillets_ni_la_bande_des_modes_ni_le_bandeau()
        {
            Servir("seigneurie-6", Zab); Canvas.ForceUpdateCanvases();
            Transform toile = racine.transform.Find("Cabinet"); Rect zone = Monde(Gestes.Panneau);
            var voisins = new List<RectTransform>(racine.GetComponents<Feuillet>().Select(f => f.Cadre).Where(c => c != null));
            Assert.That(voisins.Count, Is.GreaterThanOrEqualTo(3), "les feuillets ne sont pas tous lus");
            voisins.Add((RectTransform)toile.Find(CalquesCarte.BANDE)); voisins.Add((RectTransform)toile.Find("FORGE · Le cabinet"));
            voisins.Add((RectTransform)toile.Find("Votre maison")); voisins.Add((RectTransform)toile.Find("Territoire conservé"));
            foreach (var voisin in voisins) Assert.That(zone.Overlaps(Monde(voisin)), Is.False, "l'encart recouvre « " + voisin.name + " »");
            var cadre = Gestes.Panneau;
            Assert.That(cadre.anchoredPosition.y - cadre.sizeDelta.y, Is.GreaterThanOrEqualTo(-1056), "l'encart passe sous la bande des modes");
            Assert.That(cadre.anchoredPosition.x + cadre.sizeDelta.x, Is.LessThanOrEqualTo(764), "l'encart mord sur la bande des modes");
            foreach (var bouton in Gestes.Panneau.GetComponentsInChildren<Button>(true))
                Assert.That(zone.Contains(Monde((RectTransform)bouton.transform).min) && zone.Contains(Monde((RectTransform)bouton.transform).max), Is.True, "« " + bouton.name + " » sort de l'encart");
            foreach (var phrase in new[] { PremiersGestes.TEMPS, PremiersGestes.VILLE, PremiersGestes.ARMEE })
            { var texte = Gestes.Panneau.GetComponentsInChildren<Text>(true).Single(t => t.text == phrase);
              Assert.That(texte.preferredWidth, Is.LessThanOrEqualTo(texte.rectTransform.sizeDelta.x), "la ligne déborde : " + texte.text); }
            var lignes = Gestes.Panneau.GetComponentsInChildren<Button>(true).Where(b => b != Gestes.BoutonFermer).Select(b => Monde((RectTransform)b.transform)).ToArray();
            for (int i = 0; i < lignes.Length; i++) for (int j = i + 1; j < lignes.Length; j++) Assert.That(lignes[i].Overlaps(lignes[j]), Is.False, "deux lignes se recouvrent");
            foreach (var ligne in lignes) Assert.That(ligne.yMin, Is.GreaterThan(zone.yMin), "une ligne touche le bord bas de l'encart");
            Rect fermer = Monde((RectTransform)Gestes.BoutonFermer.transform);
            foreach (var ligne in lignes) Assert.That(fermer.Overlaps(ligne), Is.False, "« Fermer » recouvre une ligne");
        }
    }
}
