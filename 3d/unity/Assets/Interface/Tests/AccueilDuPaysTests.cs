using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using Forge.Pont;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.UI;
using Object = UnityEngine.Object;

namespace Forge.Interface.Tests
{
    // L'accueil : choisir son pays sur la carte ou parmi les départs conseillés, lire sa fiche, « Commencer ».
    // La partie, les terres de la carte et les habitants sont servis par des lecteurs témoins, à la forme du service.
    public sealed class AccueilDuPaysTests
    {
        const string RAISON_PARIS = "la ville de Paris n'est pas encore bâtie en 3D ; seule Biskra l'est";
        static readonly DateDuMonde Jour = new DateDuMonde(1400, 1);
        static FicheJouable Fiche(string id, string maison, string sorte, string pays, string nomDuPays, string siege, long cell, VilleJouable ville, params (string id, string nom)[] regne)
            => new FicheJouable(id, maison, sorte, 4, new IdentiteDePays(pays, nomDuPays),
                (regne.Length == 0 ? new[] { (pays, nomDuPays) } : regne).Select(r => new IdentiteDePays(r.Item1, r.Item2)), new SiegeJouable(siege, siege, cell), null, ville);
        static readonly FicheJouable Zab = Fiche("seigneurie-6", "Banou Mozni", "seigneurie", "seigneurie-6", "Émirat du Zab", "Biskra", 10103,
            new VilleJouable(true, "3d/unity/Assets/ForgeLocal3D/Desert/Scenes/Forge_Desert_Ville_ksar_des_sept_puits.unity", null));
        static readonly FicheJouable Bar = Fiche("seigneurie-1", "Bar", "seigneurie", "seigneurie-1", "Duché de Bar", "Bar-le-Duc", 10340,
            new VilleJouable(false, null, "la ville de Bar-le-Duc n'est pas encore bâtie en 3D ; seule Biskra l'est"));
        static readonly FicheJouable Valois = Fiche("grande-3", "Valois", "grande maison", "puissance-2", "France", "Paris", 10200, new VilleJouable(false, null, RAISON_PARIS));
        static readonly FicheJouable Luxembourg = Fiche("grande-9", "Luxembourg", "grande maison", "puissance-10", "Bohême", "Prague", 10500,
            new VilleJouable(false, null, "la ville de Prague n'est pas encore bâtie en 3D ; seule Biskra l'est"),
            ("puissance-9", "Saint-Empire"), ("puissance-10", "Bohême"), ("puissance-11", "Hongrie"));
        // Les terres de la carte : 200 en France, 500 en Bohême, 501 au Saint-Empire, 700 à Venise (une république), 900 sans maître.
        static readonly TerresDeLaCarte Terres = new TerresDeLaCarte(0, Jour, new[] {
                new PaysDeLaCarte("puissance-10", "Bohême", new IdentiteDeMaison("grande-9", "Luxembourg")),
                new PaysDeLaCarte("puissance-2", "France", new IdentiteDeMaison("grande-3", "Valois")),
                new PaysDeLaCarte("puissance-20", "Venise", new IdentiteDeMaison("institution-15", "République de Venise")),
                new PaysDeLaCarte("puissance-9", "Saint-Empire", new IdentiteDeMaison("grande-9", "Luxembourg")) },
            new[] { new TerreLue(200, "grande-3", "puissance-2", "grande-3"), new TerreLue(500, "grande-9", "puissance-10", "grande-9"),
                new TerreLue(501, "grande-29", "puissance-9", "grande-9"), new TerreLue(700, "institution-15", "puissance-20", "institution-15"), new TerreLue(900, null, null) });

        GameObject toile; AccueilDuPays accueil; LecturePartie partie;
        readonly List<string> choix = new List<string>(); int lancements; bool enPause; RecuIntention reponse; string maisonServie;
        readonly List<string> lectures = new List<string>();

        [SetUp] public void Ouvrir()
        {
            choix.Clear(); lectures.Clear(); lancements = 0; enPause = true; reponse = RecuIntention.AccepteeAu(1); maisonServie = null;
            toile = new GameObject("Toile témoin", typeof(RectTransform), typeof(Canvas));
            partie = new LecturePartie(() => Lecture<MondeAvecMaisonLu>.De(new MondeAvecMaisonLu(new MondeLu(0, Jour, 0, new CelluleDuMonde[0]), maisonServie)), _ => null,
                () => Lecture<JouablesLus>.De(new JouablesLus(0, Jour, new[] { Bar, Zab, Valois, Luxembourg })),
                id => { lock (choix) choix.Add(id); return reponse; });
            accueil = new AccueilDuPays(toile.transform, () => partie, () => Terres, Habitants, () => enPause, () => lancements++);
        }
        [TearDown] public void Fermer() => Object.DestroyImmediate(toile);

        Lecture<TerresDuPays> Habitants(string id)
        {
            lock (lectures) lectures.Add(id);
            return Lecture<TerresDuPays>.De(new TerresDuPays(id, 0, Jour, null, new string[0], new string[0], new[] { new LieuDuPays(7, 0) }, new LieuDuPays[0],
                1, id == "grande-3" ? 9876543 : 12345, 12, 0, 0, 0, null, "grenier absent", new BatimentDuPays[0]));
        }
        void Afficher()
        {
            accueil.Afficher();
            var fin = DateTime.UtcNow.AddSeconds(5); while (accueil.LectureEnVol && DateTime.UtcNow < fin) Thread.Sleep(5);
            Assert.That(accueil.LectureEnVol, Is.False, "les habitants sont encore en lecture"); accueil.Afficher();
        }
        async Task Lu() { await partie.Actualiser(); Afficher(); }
        Button Bouton(string nom) => toile.GetComponentsInChildren<Button>(true).Single(b => b.name == nom);

        [Test] public async Task Sans_pays_choisi_Commencer_est_inactif_et_dit_pourquoi()
        {
            await Lu();
            Assert.That(accueil.Ouvert, Is.True); Assert.That(accueil.Panneau.gameObject.activeSelf, Is.True); Assert.That(accueil.Panneau.name, Is.EqualTo("Choisissez votre pays"));
            Assert.That(toile.GetComponentsInChildren<Text>(true).Any(t => t.text == AccueilDuPays.PHRASE), Is.True, "la phrase de l'accueil manque");
            Assert.That(accueil.Commencer.interactable, Is.False); Assert.That(accueil.PhraseDeCommencer, Is.EqualTo(AccueilDuPays.SANS_PAYS));
            Assert.That(accueil.PhraseDeCommencer, Does.StartWith("Choisissez d'abord un pays"));
            Assert.That(accueil.TexteDuNom, Is.EqualTo(AccueilDuPays.AUCUN)); Assert.That(accueil.TexteDeLEtat, Is.EqualTo(AccueilDuPays.SANS_PAYS));
            Assert.That(toile.GetComponentsInChildren<Button>(true).Count(b => b.name == AccueilDuPays.COMMENCER), Is.EqualTo(1), "un seul bouton « Commencer »");
            await accueil.Lancer(); Assert.That(choix, Is.Empty, "rien ne part sans pays"); Assert.That(lancements, Is.Zero);
        }

        [Test] public async Task La_fiche_de_la_France_dit_son_nom_sa_maison_son_siege_ses_habitants_et_sa_ville()
        {
            await Lu(); accueil.Designer(200); Afficher();
            Assert.That(accueil.TexteDuNom, Is.EqualTo("France")); Assert.That(accueil.Montree.Id, Is.EqualTo("grande-3"));
            Assert.That(accueil.TexteDeLaFiche, Is.EqualTo("Maison : Valois\nSiège : Paris\nHabitants : " + TexteDuMonde.Nombre(9876543)
                + "\nVille à bâtir : non, pas encore de ville\nLa ville de Paris n'est pas encore bâtie en 3D ; seule Biskra l'est."));
            Assert.That(TexteDuMonde.Interdit(accueil.TexteDeLaFiche, "grande-3", "puissance-2"), Is.Null, "la fiche montre un identifiant");
            Assert.That(lectures, Is.EqualTo(new[] { "grande-3" }), "les habitants se lisent une fois, pour la maison du pays");
            Afficher(); Assert.That(lectures.Count, Is.EqualTo(1), "relus sans changer de pays");
            Assert.That(accueil.Commencer.interactable, Is.True); Assert.That(accueil.PhraseDeCommencer, Does.Contain("France"));
            accueil.Prendre(Zab); Afficher(); Assert.That(accueil.TexteDuNom, Is.EqualTo("Émirat du Zab")); Assert.That(accueil.TexteDeLaFiche, Does.EndWith("\nVille à bâtir : oui"));
        }

        [Test] public async Task Un_clic_sur_la_Boheme_ouvre_la_fiche_de_la_Boheme_maison_Luxembourg()
        {
            await Lu(); accueil.Designer(500); Afficher();
            Assert.That(accueil.TexteDuNom, Is.EqualTo("Bohême")); Assert.That(accueil.Montree.Id, Is.EqualTo("grande-9"));
            Assert.That(accueil.TexteDeLaFiche, Does.StartWith("Maison : Luxembourg\nRègne aussi sur : Saint-Empire, Hongrie\nSiège : Prague"));
            accueil.Designer(501); Afficher();
            Assert.That(accueil.TexteDuNom, Is.EqualTo("Saint-Empire"), "une terre d'un vassal se lit au pays où elle est"); Assert.That(accueil.Montree.Id, Is.EqualTo("grande-9"));
            Assert.That(accueil.TexteDeLaFiche, Does.StartWith("Maison : Luxembourg\nRègne aussi sur : Bohême, Hongrie"));
            accueil.Designer(900); Afficher(); Assert.That(accueil.TexteDuNom, Is.EqualTo("Saint-Empire"), "une terre sans pays ne change pas le pays montré");
            Assert.That(TexteDuMonde.Interdit(accueil.TexteDeLaFiche, "grande-9", "puissance-9", "puissance-10"), Is.Null);
        }

        [Test] public async Task Commencer_depose_le_choix_par_maison_puis_lance_le_temps_une_seule_fois()
        {
            await Lu(); Bouton("Émirat du Zab").onClick.Invoke(); Afficher();
            Assert.That(accueil.Montree.Id, Is.EqualTo("seigneurie-6"));
            await accueil.Lancer(); Afficher();
            Assert.That(choix, Is.EqualTo(new[] { "seigneurie-6" }), "le choix part par l'identifiant de la maison"); Assert.That(lancements, Is.EqualTo(1));
            Assert.That(LecturePartie.IntentionDeChoix(choix[0]), Is.EqualTo("{\"type\":\"choisir_depart\",\"maison\":\"seigneurie-6\"}"));
            Assert.That(accueil.TexteDeLEtat, Is.EqualTo(AccueilDuPays.CHOIX_RECU)); Assert.That(accueil.Commencer.interactable, Is.False, "un choix reçu ne se renvoie pas");
            Assert.That(Bouton("Duché de Bar").interactable, Is.False, "un choix reçu ferme la liste");
            await accueil.Lancer(); await accueil.Lancer(); Assert.That(choix.Count, Is.EqualTo(1)); Assert.That(lancements, Is.EqualTo(1), "le temps est lancé une seule fois");
            // La maison servie ferme l'accueil, qui ne revient pas.
            maisonServie = "seigneurie-6"; await Lu(); Assert.That(accueil.Ouvert, Is.False); Assert.That(accueil.Panneau.gameObject.activeSelf, Is.False);
            maisonServie = null; await Lu(); Assert.That(accueil.Ouvert, Is.False);
        }

        [Test] public async Task Un_temps_qui_file_ou_un_refus_ne_lance_rien_de_plus()
        {
            enPause = false; await Lu(); accueil.Designer(200); Afficher(); await accueil.Lancer();
            Assert.That(choix, Is.EqualTo(new[] { "grande-3" })); Assert.That(lancements, Is.Zero, "le temps file déjà : il n'est pas basculé");
            Fermer(); Ouvrir(); reponse = RecuIntention.Refusee(409, "départ déjà choisi : seigneurie-1");
            await Lu(); accueil.Prendre(Bar); Afficher(); await accueil.Lancer(); Afficher();
            Assert.That(lancements, Is.Zero, "un refus ne lance pas le temps"); Assert.That(accueil.TexteDeLEtat, Does.StartWith("Demande refusée : "));
            Assert.That(TexteDuMonde.Interdit(accueil.TexteDeLEtat, "seigneurie-1"), Is.Null, "le refus montre un identifiant");
        }

        [Test] public async Task Un_pays_que_le_monde_ne_propose_pas_garde_Commencer_grise_avec_sa_raison()
        {
            await Lu(); accueil.Designer(700); Afficher();
            Assert.That(accueil.Montree, Is.Null); Assert.That(accueil.TexteDuNom, Is.EqualTo("Venise")); Assert.That(accueil.TexteDeLaFiche, Is.EqualTo("Maison : République de Venise"));
            Assert.That(accueil.Commencer.interactable, Is.False); Assert.That(accueil.PhraseDeCommencer, Is.EqualTo(AccueilDuPays.NON_JOUABLE)); Assert.That(accueil.TexteDeLEtat, Is.EqualTo(AccueilDuPays.NON_JOUABLE));
            await accueil.Lancer(); Assert.That(choix, Is.Empty); Assert.That(lectures, Is.Empty, "aucun habitant lu pour un pays sans fiche");
        }

        [Test] public async Task Les_departs_conseilles_sont_les_seigneuries_servies_nommees_par_leur_pays()
        {
            Assert.That(accueil.Conseilles(), Is.Empty, "rien de conseillé avant la lecture");
            await Lu();
            var liste = accueil.Panneau.Find(AccueilDuPays.LISTE).GetComponentsInChildren<Button>(true).Select(b => b.name).ToArray();
            Assert.That(liste, Is.EqualTo(new[] { "Duché de Bar", "Émirat du Zab" }));
            Assert.That(accueil.Conseilles().Select(f => f.Siege.CellId), Is.EqualTo(new long?[] { 10340, 10103 }));
            Assert.That(CabinetDeCarte.CommandesSansPhrase(toile.transform), Is.Empty);
            // Avant que les terres soient lues, le siège d'un départ conseillé se reconnaît encore.
            accueil = new AccueilDuPays(toile.transform, () => partie, () => null, Habitants, () => enPause, () => lancements++); Afficher();
            accueil.Designer(10103); Afficher(); Assert.That(accueil.Montree.Id, Is.EqualTo("seigneurie-6"));
            accueil.Designer(200); Afficher(); Assert.That(accueil.Montree.Id, Is.EqualTo("seigneurie-6"), "sans terres lues, une autre terre ne montre rien");
        }

        [Test] public void Les_textes_de_l_accueil_tiennent_dans_leur_cadre()
        {
            var panneau = accueil.Panneau; Assert.That(panneau.sizeDelta, Is.EqualTo(new Vector2(584, 932)));
            var cadres = panneau.Cast<Transform>().Where(t => t.name != "Filet").Cast<RectTransform>().ToArray();
            foreach (var c in cadres)
            {
                Assert.That(c.anchoredPosition.x >= 0 && c.anchoredPosition.x + c.sizeDelta.x <= 584 && -c.anchoredPosition.y + c.sizeDelta.y <= 932, Is.True, c.name + " sort du panneau");
            }
            var commencer = (RectTransform)accueil.Commencer.transform; var fiche = toile.GetComponentsInChildren<Text>(true).Single(t => t.name == AccueilDuPays.FICHE).rectTransform;
            Assert.That(-commencer.anchoredPosition.y, Is.GreaterThanOrEqualTo(-fiche.anchoredPosition.y + fiche.sizeDelta.y), "la fiche descend sur « Commencer »");
            Assert.That(commencer.sizeDelta.y, Is.GreaterThan(SocleInterface.HauteurCommande), "« Commencer » est un gros bouton");
            var texte = toile.GetComponentsInChildren<Text>(true).Single(t => t.name == AccueilDuPays.FICHE);
            texte.text = "Maison : Luxembourg\nRègne aussi sur : Saint-Empire, Hongrie\nSiège : Prague\nSuzerain : Hafsides (Ifriqiya)\nHabitants : " + TexteDuMonde.Nombre(12345678)
                + "\nVille à bâtir : non, pas encore de ville\nLa ville de Prague n'est pas encore bâtie en 3D ; seule Biskra l'est.";
            Assert.That(texte.preferredHeight, Is.LessThanOrEqualTo(texte.rectTransform.sizeDelta.y), "la plus longue fiche déborde");
        }
    }
}
