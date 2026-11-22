using System;
using System.Linq;
using NUnit.Framework;

namespace Forge.Pont.Tests
{
    // Ce que la barre des outils montre d'après l'état de l'outil : les boutons visibles, l'outil en main enfoncé, la caserne et
    // son grain, la seule ligne d'aide. Le devis est celui que le monde sert ; rien ne se recalcule.
    public sealed class OutilsDeLaVilleTests
    {
        static BatimentDeLevee Devis(double cout = 2400, double manque = 0, string refus = null) =>
            new BatimentDeLevee("caserne", "Caserne", 10465, 800, 25, cout, manque, refus);
        static CompositionDesOutils Composer(OutilDeLaVille outil, int points = 0, BatimentDeLevee devis = null, CaserneDeLaVille caserne = CaserneDeLaVille.Aucune,
            IssueDuGeste issue = IssueDuGeste.Aucune, string texte = null) =>
            OutilsDeLaVille.Composer(new EtatDesOutils { Outil = outil, Points = points, Devis = devis ?? Devis(), Caserne = caserne, Issue = issue, Texte = texte });

        [Test] public void Sans_outil_valider_et_annuler_sont_caches()
        {
            var c = Composer(OutilDeLaVille.Aucun);
            Assert.IsFalse(c[GesteDeLaVille.Valider].Visible); Assert.IsFalse(c[GesteDeLaVille.Annuler].Visible);
            foreach (var g in new[] { GesteDeLaVille.Rue, GesteDeLaVille.Parcelle, GesteDeLaVille.Caserne, GesteDeLaVille.Retour }) Assert.IsTrue(c[g].Visible, g.ToString());
            Assert.IsFalse(c.Boutons.Any(b => b.Enfonce));
            Assert.AreEqual(OutilsDeLaVille.SANS_OUTIL, c.Ligne);
        }

        [Test] public void Le_bouton_de_l_outil_en_main_est_enfonce_et_lui_seul()
        {
            foreach (var (outil, geste) in new[] { (OutilDeLaVille.Rue, GesteDeLaVille.Rue), (OutilDeLaVille.Parcelle, GesteDeLaVille.Parcelle), (OutilDeLaVille.Caserne, GesteDeLaVille.Caserne) })
            {
                var c = Composer(outil);
                CollectionAssert.AreEqual(new[] { geste }, c.Boutons.Where(b => b.Enfonce).Select(b => b.Geste).ToArray(), outil.ToString());
                Assert.IsTrue(c[GesteDeLaVille.Annuler].Visible, outil.ToString());
            }
        }

        [Test] public void Valider_suit_les_points_du_trace_et_se_cache_pour_un_clic_sur_parcelle()
        {
            Assert.IsFalse(Composer(OutilDeLaVille.Rue, 1)[GesteDeLaVille.Valider].Actif); Assert.IsTrue(Composer(OutilDeLaVille.Rue, 2)[GesteDeLaVille.Valider].Actif);
            Assert.IsFalse(Composer(OutilDeLaVille.Parcelle, 1)[GesteDeLaVille.Valider].Actif); Assert.IsTrue(Composer(OutilDeLaVille.Parcelle, 2)[GesteDeLaVille.Valider].Actif);
            Assert.IsFalse(Composer(OutilDeLaVille.Enceinte, 2)[GesteDeLaVille.Valider].Actif); Assert.IsTrue(Composer(OutilDeLaVille.Enceinte, 3)[GesteDeLaVille.Valider].Actif);
            Assert.AreEqual("Il faut au moins deux points.", Composer(OutilDeLaVille.Rue, 1)[GesteDeLaVille.Valider].Raison);
            Assert.IsFalse(Composer(OutilDeLaVille.Caserne)[GesteDeLaVille.Valider].Visible); Assert.IsFalse(Composer(OutilDeLaVille.Batiment)[GesteDeLaVille.Valider].Visible);
        }

        [Test] public void Chaque_libelle_porte_son_raccourci()
        {
            var c = Composer(OutilDeLaVille.Rue, 2);
            foreach (var (geste, nom, touche) in OutilsDeLaVille.Gestes) StringAssert.StartsWith(nom + " (" + touche + ")", c[geste].Libelle);
            Assert.AreEqual("Rue (R)", c[GesteDeLaVille.Rue].Libelle); Assert.AreEqual("Retour à la carte (C)", c[GesteDeLaVille.Retour].Libelle);
        }

        [Test] public void La_caserne_payable_dit_son_prix_et_s_active()
        {
            var b = Composer(OutilDeLaVille.Aucun, devis: Devis(2400))[GesteDeLaVille.Caserne];
            Assert.IsTrue(b.Actif); Assert.AreEqual("Caserne (4)\n2,40 t de grain", b.Libelle); Assert.IsNull(b.Raison);
        }

        [Test] public void La_caserne_grisee_dit_le_grain_qui_manque_tel_que_le_monde_le_sert()
        {
            var c = Composer(OutilDeLaVille.Caserne, devis: Devis(2400, 615.5, "grenier insuffisant : 2400 kg de grain demandés, 1784.5 kg disponibles"));
            var b = c[GesteDeLaVille.Caserne];
            Assert.IsFalse(b.Actif); Assert.AreEqual("Caserne (4)\nil manque 615,5 kg de grain", b.Libelle);
            // L'outil en main, la ligne dit pourquoi la caserne ne se pose pas.
            Assert.AreEqual("Le grenier ne paie pas la caserne : il manque 615,5 kg de grain.", c.Ligne);
        }

        [Test] public void Un_autre_refus_du_monde_grise_la_caserne_par_son_debut()
        {
            var b = Composer(OutilDeLaVille.Aucun, devis: Devis(refus: "pas assez de bras : 25 paysans par jour demandés, 10 dans la cellule"))[GesteDeLaVille.Caserne];
            Assert.IsFalse(b.Actif); Assert.AreEqual("Caserne (4)\npas assez de bras", b.Libelle); Assert.AreEqual("Caserne refusée.", b.Raison);
            Assert.AreEqual("Caserne (4)\nrefusée aujourd'hui", Composer(OutilDeLaVille.Aucun, devis: Devis(refus: "pas sur vos terres 10465"))[GesteDeLaVille.Caserne].Libelle);
        }

        // Le monde refuse une seconde caserne : une fois la première déposée ou au plan, rien ne parle plus de refus.
        [Test] public void La_caserne_deposee_ou_au_plan_ne_dit_aucun_refus()
        {
            var refusee = Devis(refus: "une seule caserne par province : la cellule 10465 en a déjà une");
            foreach (var etat in new[] { CaserneDeLaVille.Deposee, CaserneDeLaVille.EnChantier, CaserneDeLaVille.Batie })
                foreach (var outil in new[] { OutilDeLaVille.Aucun, OutilDeLaVille.Caserne })
                {
                    var c = Composer(outil, devis: refusee, caserne: etat); var b = c[GesteDeLaVille.Caserne];
                    Assert.IsFalse(b.Actif, etat.ToString());
                    foreach (string texte in new[] { b.Libelle, b.Raison, c.Ligne }) StringAssert.DoesNotContain("refus", texte, etat + " " + outil);
                }
            Assert.AreEqual("Caserne (4)\nen chantier", Composer(OutilDeLaVille.Aucun, devis: refusee, caserne: CaserneDeLaVille.EnChantier)[GesteDeLaVille.Caserne].Libelle);
        }

        [Test] public void Sans_devis_la_caserne_est_grisee_et_nomme_l_absence()
        {
            var c = OutilsDeLaVille.Composer(new EtatDesOutils { Outil = OutilDeLaVille.Caserne, AbsenceDuDevis = "aucune maison choisie" });
            Assert.IsFalse(c[GesteDeLaVille.Caserne].Actif); Assert.AreEqual("Caserne (4)\nprix non lu", c[GesteDeLaVille.Caserne].Libelle);
            Assert.AreEqual("Prix de la caserne non lu : aucune maison choisie", c.Ligne);
        }

        [Test] public void La_ligne_dit_le_geste_suivant()
        {
            Assert.AreEqual("Cliquez le départ de la rue.", Composer(OutilDeLaVille.Rue, 0).Ligne);
            Assert.AreEqual("Cliquez le point suivant de la rue.", Composer(OutilDeLaVille.Rue, 1).Ligne);
            Assert.AreEqual("Cliquez le coin opposé, au fond de la parcelle.", Composer(OutilDeLaVille.Parcelle, 1).Ligne);
            Assert.AreEqual("Cliquez une parcelle achevée pour y poser la caserne.", Composer(OutilDeLaVille.Caserne).Ligne);
            Assert.AreEqual("Caserne déposée : son chantier s'ouvre demain.", Composer(OutilDeLaVille.Caserne, issue: IssueDuGeste.Depot).Ligne);
        }

        [Test] public void Un_refus_se_dit_et_son_identifiant_se_tait()
        {
            Assert.AreEqual("Route refusée par le relief : pente trop forte.", Composer(OutilDeLaVille.Rue, issue: IssueDuGeste.Refus, texte: "Route refusée par le relief : pente trop forte.").Ligne);
            Assert.AreEqual("Le monde refuse la parcelle.", Composer(OutilDeLaVille.Parcelle, issue: IssueDuGeste.Refus, texte: "Le monde refuse la parcelle : la rue 12 n'est pas dans la cellule 10103").Ligne);
            Assert.AreEqual(OutilsDeLaVille.GESTE_REFUSE, Composer(OutilDeLaVille.Parcelle, issue: IssueDuGeste.Refus, texte: "rue 12 : absente").Ligne);
            // Un avis qui montrerait un nombre nu se tait : la ligne rend le geste suivant.
            Assert.AreEqual("Valider pour déposer la parcelle, ou cliquez un autre coin du fond.", Composer(OutilDeLaVille.Parcelle, 2, issue: IssueDuGeste.Avis, texte: "Parcelle 7 possible").Ligne);
        }

        // Chaque état a sa ligne, jamais vide, sans identifiant ni nombre sans unité.
        [Test] public void Une_ligne_par_etat_jamais_vide_ni_nombre_nu()
        {
            int vus = 0;
            foreach (OutilDeLaVille outil in Enum.GetValues(typeof(OutilDeLaVille)))
                foreach (IssueDuGeste issue in Enum.GetValues(typeof(IssueDuGeste)))
                    foreach (CaserneDeLaVille caserne in Enum.GetValues(typeof(CaserneDeLaVille)))
                        for (int points = 0; points <= 4; points++)
                            foreach (var devis in new[] { Devis(), Devis(2400, 615.5, "grenier insuffisant : 2400 kg"), null })
                            {
                                var c = OutilsDeLaVille.Composer(new EtatDesOutils { Outil = outil, Points = points, Issue = issue, Caserne = caserne, Devis = devis, Nature = "scierie" });
                                string ici = outil + " " + issue + " " + caserne + " " + points;
                                Assert.IsFalse(string.IsNullOrWhiteSpace(c.Ligne), ici);
                                // Un libellé se juge sans son raccourci : « (4) » nomme une touche, pas un nombre du monde.
                                var libelles = c.Boutons.Select(b => b.Libelle.Replace(OutilsDeLaVille.Libelle(b.Geste), ""));
                                foreach (string texte in libelles.Concat(c.Boutons.Select(b => b.Raison)).Append(c.Ligne).Where(t => t != null))
                                {
                                    Assert.IsNull(TexteDuMonde.Interdit(texte), ici + " : " + texte); Assert.IsNull(TexteDuMonde.SansUnite(texte), ici + " : " + texte);
                                }
                                vus++;
                            }
            Assert.AreEqual(6 * 4 * 4 * 5 * 3, vus);
        }
    }
}
