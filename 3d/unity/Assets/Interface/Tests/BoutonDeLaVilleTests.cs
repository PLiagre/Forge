using System.Collections.Generic;
using System.Linq;
using Forge.Pont;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.UI;
using Object = UnityEngine.Object;

namespace Forge.Interface.Tests
{
    // « Entrer dans la ville », dans le bandeau du vrai cabinet : visible une fois la maison servie, actif seulement si le service
    // dit sa capitale bâtie ; un clic passe par le passage à la capitale posé sur la carte, avec la scène et le siège servis.
    public sealed class BoutonDeLaVilleTests
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
            chargees.Clear(); PassageALaCapitale.PrendreCelluleRemise(string.Empty);
            racine = new GameObject("Carte de contrôle", typeof(CarteDessinee), typeof(HorlogeDeCarte), typeof(FicheDeCellule), typeof(ReperesDeDepart));
            passage = racine.AddComponent<PassageALaCapitale>(); passage.ChargerScene = nom => chargees.Add(nom);
            cabinet = racine.AddComponent<CabinetDeCarte>(); cabinet.Construire();
            partie = new LecturePartie(() => null, _ => null, () => null, _ => null); cabinet.Partie = partie;
        }
        [TearDown] public void Fermer() { racine.GetComponent<CarteDessinee>().Arreter(); Object.DestroyImmediate(racine); }

        static void Poser(object cible, string nom, object valeur) => cible.GetType().GetProperty(nom).GetSetMethod(true).Invoke(cible, new[] { valeur });
        void Servir(string maison, params FicheJouable[] fiches)
        {
            Poser(partie, "Monde", Lecture<MondeAvecMaisonLu>.De(new MondeAvecMaisonLu(new MondeLu(1, Jour, 0, new CelluleDuMonde[0]), maison)));
            Poser(partie, "Jouables", fiches.Length == 0 ? null : Lecture<JouablesLus>.De(new JouablesLus(1, Jour, fiches)));
            cabinet.Afficher();
        }
        Button Bouton => racine.GetComponentsInChildren<Button>(true).Single(b => b.name == BoutonDeLaVille.NOM);

        [Test] public void Sans_maison_choisie_le_bouton_est_cache()
        {
            Assert.That(Bouton.gameObject.activeSelf, Is.False, "visible avant toute lecture");
            Servir(null, Zab, Valois); Assert.That(Bouton.gameObject.activeSelf, Is.False, "visible sans maison du joueur");
            Assert.That(Bouton.transform.parent.name, Is.EqualTo("FORGE · Le cabinet"), "le bouton n'est pas dans le bandeau");
        }

        [Test] public void Pour_la_France_il_est_grise_et_son_infobulle_dit_la_raison_servie()
        {
            Servir("grande-3", Zab, Valois);
            Assert.That(Bouton.gameObject.activeSelf, Is.True); Assert.That(Bouton.interactable, Is.False);
            Assert.That(cabinet.Ville.Phrase, Is.EqualTo("La ville de Paris n'est pas encore bâtie en 3D ; seule Biskra l'est."));
            Assert.That(Bouton.GetComponent<Infobulle>().Phrase, Is.EqualTo(cabinet.Ville.Phrase));
            Bouton.onClick.Invoke(); CollectionAssert.IsEmpty(chargees, "le bouton grisé a ouvert une ville"); Assert.That(passage.SceneDemandee, Is.Null);
            Assert.That(TexteDuMonde.Interdit(cabinet.Ville.Phrase, "grande-3", "puissance-2"), Is.Null);
        }

        [Test] public void Pour_le_Zab_il_ouvre_le_ksar_sur_le_siege_servi_une_seule_fois()
        {
            Servir("seigneurie-6", Zab, Valois);
            Assert.That(Bouton.gameObject.activeSelf && Bouton.interactable, Is.True, "le bouton du Zab n'est pas actif");
            Assert.That(cabinet.Ville.Phrase, Is.EqualTo("Ouvre Biskra, votre capitale."));
            Bouton.onClick.Invoke();
            CollectionAssert.AreEqual(new[] { TerresAvecKit.Scenes["seigneurie-6"] }, chargees, "la scène servie n'est pas celle du ksar");
            Assert.That(PassageALaCapitale.PrendreCelluleRemise(TerresAvecKit.Scenes["seigneurie-6"]), Is.EqualTo(10103L), "la remise ne porte pas le siège servi");
            cabinet.Afficher(); Assert.That(Bouton.interactable, Is.False, "le bouton reste actif après la descente");
            Bouton.onClick.Invoke(); Assert.That(chargees.Count, Is.EqualTo(1), "la ville s'ouvre deux fois");
        }

        [Test] public void Sans_fiche_lue_ou_sans_monde_il_reste_visible_et_grise()
        {
            Servir("seigneurie-6"); Assert.That(Bouton.gameObject.activeSelf, Is.True); Assert.That(Bouton.interactable, Is.False);
            Assert.That(cabinet.Ville.Phrase, Is.EqualTo(BoutonDeLaVille.LECTURE));
            Servir("seigneurie-6", Zab); Assert.That(Bouton.interactable, Is.True);
            Poser(partie, "Monde", Lecture<MondeAvecMaisonLu>.Absent("service coupé")); cabinet.Afficher();
            Assert.That(Bouton.gameObject.activeSelf, Is.True, "une coupure cache le bouton"); Assert.That(Bouton.interactable, Is.False, "une coupure laisse le bouton actif");
        }

        static Rect Monde(RectTransform t) { var c = new Vector3[4]; t.GetWorldCorners(c); return Rect.MinMaxRect(c.Min(v => v.x), c.Min(v => v.y), c.Max(v => v.x), c.Max(v => v.y)); }
        [Test] public void Il_ne_recouvre_aucune_commande_voisine_du_bandeau()
        {
            Servir("seigneurie-6", Zab); Canvas.ForceUpdateCanvases();
            Transform toile = racine.transform.Find("Cabinet"); var bandeau = (RectTransform)toile.Find("FORGE · Le cabinet");
            Rect zone = Monde((RectTransform)Bouton.transform), barre = Monde(bandeau);
            Assert.That(barre.Contains(zone.min) && barre.Contains(zone.max), Is.True, "le bouton sort du bandeau");
            var date = bandeau.GetComponentsInChildren<Text>(true).Single(t => t.name == "Lecture de la date…");
            var voisins = new List<RectTransform> { date.rectTransform, (RectTransform)bandeau.Find(CabinetDeCarte.DOSSIERS), (RectTransform)bandeau.Find(CabinetDeCarte.PAYS), (RectTransform)toile.Find("Menu") };
            voisins.AddRange(bandeau.GetComponentsInChildren<Button>(true).Where(b => b != Bouton && b.transform.parent == bandeau).Select(b => (RectTransform)b.transform));
            Assert.That(voisins.Count, Is.GreaterThanOrEqualTo(7), "les voisins du bouton ne sont pas tous lus");
            foreach (var voisin in voisins) Assert.That(zone.Overlaps(Monde(voisin)), Is.False, "le bouton recouvre « " + voisin.name + " »");
            var texte = Bouton.GetComponentInChildren<Text>(); Assert.That(texte.preferredWidth, Is.LessThanOrEqualTo(BoutonDeLaVille.LARGEUR), "son nom déborde");
            foreach (string ecrit in new[] { "Date indisponible : le monde ne répond pas", HorlogeDeCarte.Decrire(new HorlogeLue(364, new DateDuMonde(1400, 365), 1.5)) })
            { date.text = ecrit; Assert.That(date.preferredWidth, Is.LessThanOrEqualTo(date.rectTransform.sizeDelta.x), "la date raccourcie déborde : " + ecrit); }
        }
    }
}
