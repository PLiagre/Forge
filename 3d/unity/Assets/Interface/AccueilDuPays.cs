using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using Forge.Pont;
using UnityEngine;
using UnityEngine.UI;

namespace Forge.Interface
{
    // L'accueil, tant que le monde n'a pas servi de maison du joueur : on y choisit son pays sur la carte ou parmi les départs
    // conseillés, on lit sa fiche, et « Commencer » envoie le choix ; le temps reste en pause jusqu'à ce que le joueur le lance. Tout ce qui s'écrit vient de `/jouables`,
    // de `/terres` (le pays d'une terre, sa maison et les habitants du pays seul) et de `/pays` (les habitants de la maison avec ses
    // vassaux) : l'accueil n'additionne rien, et chaque nombre dit ce qu'il compte.
    // Une classe simple : le cabinet l'appelle à chaque image, et lui passe les terres cliquées sur la carte.
    public sealed class AccueilDuPays
    {
        public const string TITRE = "Choisissez votre pays", CONSEILLES = "Départs conseillés", COMMENCER = "Commencer";
        public const string PHRASE = "Cliquez votre pays sur la carte, ou prenez un départ conseillé.";
        public const string NOM = "Nom du pays", FICHE = "Fiche du pays", ETAT = "État du choix", LISTE = "Départs proposés";
        public const string SANS_PAYS = "Choisissez d'abord un pays : cliquez-le sur la carte, ou prenez un départ conseillé.";
        public const string NON_JOUABLE = "Le monde ne propose pas ce pays au joueur : choisissez-en un autre.";
        public const string CHOIX_RECU = "Choix reçu. Le temps reste en pause : « Reprendre », en haut à droite, le lance.";
        public const string AUCUN = "Aucun pays choisi", INVITATION = "Cliquez un pays sur la carte : sa fiche s'ouvre ici.";
        const string SANS_NOM = "Pays sans nom", MAISON_SANS_NOM = "maison non nommée par le monde";
        const float X = 1312, Y = 124, LARGEUR = 584, HAUTEUR = 932, INTERIEUR = 536, HAUTEUR_COMMENCER = 72;

        readonly RectTransform panneau, liste;
        readonly Text nom, fiche, etat;
        readonly Button commencer;
        readonly Infobulle bulle;
        readonly Func<LecturePartie> partie;
        readonly Func<TerresDeLaCarte> terres;
        readonly Func<string, Lecture<TerresDuPays>> lireHabitants;
        // Le pays montré : sa fiche jouable (nulle pour un pays que le monde ne propose pas), son identifiant, son nom et sa maison servis.
        FicheJouable montree; string paysMontre, nomMontre; IdentiteDeMaison maisonMontree; bool designe;
        bool maisonVue, envoi;
        string cleDeLaListe;
        (string maison, Lecture<TerresDuPays> lu) habitants; Task<(string, Lecture<TerresDuPays>)> vol;

        public RectTransform Panneau => panneau;
        public Button Commencer => commencer;
        // Ouvert tant qu'aucune maison du joueur n'a été servie ; il ne revient pas si le monde manque ensuite.
        public bool Ouvert => !maisonVue;
        public bool LectureEnVol => vol != null && !vol.IsCompleted;
        public FicheJouable Montree => montree;
        public string TexteDuNom => nom.text;
        public string TexteDeLaFiche => fiche.text;
        public string TexteDeLEtat => etat.text;
        public string PhraseDeCommencer => bulle.Phrase;

        public AccueilDuPays(Transform toile, Func<LecturePartie> partie, Func<TerresDeLaCarte> terres, Func<string, Lecture<TerresDuPays>> lireHabitants)
        {
            this.partie = partie; this.terres = terres; this.lireHabitants = lireHabitants;
            panneau = SocleInterface.Panneau(toile, TITRE, X, Y, LARGEUR, HAUTEUR);
            var phrase = SocleInterface.Texte(panneau, PHRASE, SocleInterface.Espacement, 86, INTERIEUR); phrase.rectTransform.sizeDelta = new Vector2(INTERIEUR, 52);
            SocleInterface.Rubrique(panneau, CONSEILLES, SocleInterface.Espacement, 150, INTERIEUR);
            liste = SocleInterface.Cadre(panneau, LISTE, SocleInterface.Espacement, 210, INTERIEUR, 148);
            SocleInterface.Separateur(panneau, SocleInterface.Espacement, 376, INTERIEUR);
            nom = SocleInterface.Texte(panneau, AUCUN, SocleInterface.Espacement, 396, INTERIEUR, SocleInterface.Titre); nom.name = NOM;
            nom.rectTransform.sizeDelta = new Vector2(INTERIEUR, 40); nom.color = SocleInterface.Couleur("sang");
            fiche = SocleInterface.Texte(panneau, INVITATION, SocleInterface.Espacement, 444, INTERIEUR); fiche.name = FICHE;
            fiche.rectTransform.sizeDelta = new Vector2(INTERIEUR, 300);
            etat = SocleInterface.Texte(panneau, "", SocleInterface.Espacement, 756, INTERIEUR); etat.name = ETAT;
            etat.rectTransform.sizeDelta = new Vector2(INTERIEUR, 64); etat.color = SocleInterface.Couleur("secondaire");
            commencer = SocleInterface.Commande(panneau, COMMENCER, SocleInterface.Espacement, HAUTEUR - SocleInterface.Espacement - HAUTEUR_COMMENCER,
                () => _ = Lancer(), false, SANS_PAYS);
            commencer.GetComponent<RectTransform>().sizeDelta = new Vector2(INTERIEUR, HAUTEUR_COMMENCER);
            var ecrit = commencer.GetComponentInChildren<Text>(); ecrit.rectTransform.sizeDelta = new Vector2(INTERIEUR, HAUTEUR_COMMENCER); ecrit.fontSize = SocleInterface.Titre;
            MatieresCabinet.Engagement(commencer);
            bulle = commencer.GetComponent<Infobulle>();
            foreach (var texte in panneau.GetComponentsInChildren<Text>(true)) texte.supportRichText = false;
        }

        // Les départs conseillés servis, dans l'ordre servi : les seigneuries de départ. Vide tant que les jouables ne sont pas lus.
        public IReadOnlyList<FicheJouable> Conseilles()
        {
            var lus = partie()?.Jouables;
            return lus == null || !lus.Presente ? new FicheJouable[0] : lus.Donnees.Fiches.Where(f => f.Sorte == "seigneurie").ToArray();
        }

        // Un clic sur une terre de la carte : son pays servi, la maison de ce pays, puis sa fiche jouable. Avant que les terres soient
        // lues, seul le siège d'un départ conseillé se reconnaît. Une terre sans pays ne change pas le pays montré.
        public void Designer(long cellId)
        {
            if (!Ouvert) return;
            var lues = terres();
            string pays = lues?.PaysDe(cellId);
            if (pays == null)
            {
                var siege = Conseilles().FirstOrDefault(f => f.Siege.CellId == cellId);
                if (siege != null) Prendre(siege);
                return;
            }
            var maison = lues.MaisonDuPays(pays);
            var lus = partie()?.Jouables;
            var trouvee = maison == null || lus == null || !lus.Presente ? null : lus.Donnees.Fiches.FirstOrDefault(f => f.Id == maison.Id);
            (montree, paysMontre, nomMontre, maisonMontree, designe) = (trouvee, pays, lues.NomDuPays(pays), maison, true);
        }

        // Un départ conseillé : son pays est celui de sa fiche.
        public void Prendre(FicheJouable jouable)
        {
            if (jouable == null) return;
            (montree, paysMontre, nomMontre, maisonMontree, designe) = (jouable, jouable.Pays.Id, jouable.Pays.Nom, null, true);
        }

        // Envoie le choix du pays montré, une seule requête à la fois. Le temps n'est pas touché : le monde ouvert en pause y reste,
        // et le joueur le lance par la commande du temps, que le cabinet met en avant.
        public async Task Lancer()
        {
            var lue = partie(); var choisie = montree;
            if (choisie == null || lue == null || !lue.PeutChoisir || envoi) return;
            envoi = true;
            try { await lue.Choisir(choisie.Id); }
            finally { envoi = false; }
        }

        public void Afficher()
        {
            var lue = partie(); var monde = lue?.Monde;
            if (monde != null && monde.Presente && monde.Donnees.MaisonDuJoueur != null) maisonVue = true;
            panneau.gameObject.SetActive(Ouvert);
            if (!Ouvert) return;
            AfficherLaListe(lue);
            var lus = lue?.Jouables;
            if (montree != null && lus != null && lus.Presente) montree = lus.Donnees.Fiches.FirstOrDefault(f => f.Id == montree.Id) ?? montree; // la fiche du jour servi
            LireLesHabitants();
            EcrireLaFiche();
            bool recu = lue?.Recu?.Acceptee == true;
            commencer.interactable = montree != null && lue != null && lue.PeutChoisir && !envoi;
            bulle.phrase = !designe ? SANS_PAYS : montree == null ? NON_JOUABLE : recu ? CHOIX_RECU
                : "Prend " + Nom() + " : le temps reste en pause, et le monde applique votre choix dès que vous le lancez.";
            etat.text = Etat(lue);
        }

        string Nom() => nomMontre ?? montree?.Pays.Nom ?? SANS_NOM;

        string Etat(LecturePartie lue)
        {
            var monde = lue?.Monde;
            if (monde == null) return "Lecture du monde…";
            if (!monde.Presente) return "Monde indisponible : " + TexteDuMonde.Absence(monde.Absence);
            if (lue.Jouables == null) return "Lecture des pays…";
            if (!lue.Jouables.Presente) return "Pays indisponibles : " + TexteDuMonde.Absence(lue.Jouables.Absence);
            var recu = lue.Recu;
            if (recu != null)
                return recu.Acceptee ? CHOIX_RECU : recu.Presente ? "Demande refusée : " + TexteDuMonde.Absence(recu.Erreur) : "Envoi non confirmé : " + TexteDuMonde.Absence(recu.Absence);
            return !designe ? SANS_PAYS : montree == null ? NON_JOUABLE : "";
        }

        void AfficherLaListe(LecturePartie lue)
        {
            var conseilles = Conseilles();
            string cle = string.Join("\n", conseilles.Select(f => f.Id + " " + f.Pays.Nom));
            if (cle != cleDeLaListe)
            {
                cleDeLaListe = cle;
                for (int i = liste.childCount - 1; i >= 0; i--) Detruire(liste.GetChild(i).gameObject);
                for (int i = 0; i < conseilles.Count; i++)
                {
                    var f = conseilles[i];
                    var bouton = SocleInterface.Commande(liste, f.Pays.Nom ?? SANS_NOM, i % 2 * 276, i / 2 * 52, () => Prendre(f),
                        phrase: "Montre la fiche de ce pays, sans rien envoyer au monde.");
                    bouton.GetComponent<RectTransform>().sizeDelta = new Vector2(260, SocleInterface.HauteurCommande);
                    var ecrit = bouton.GetComponentInChildren<Text>(); ecrit.rectTransform.sizeDelta = new Vector2(260, SocleInterface.HauteurCommande); ecrit.supportRichText = false;
                }
            }
            bool libre = lue?.Recu?.Acceptee != true;
            foreach (var bouton in liste.GetComponentsInChildren<Button>()) bouton.interactable = libre;
        }

        // Les habitants de la maison montrée, lus hors du fil principal, une fois par maison montrée.
        void LireLesHabitants()
        {
            if (vol != null && vol.IsCompleted)
            {
                var fini = vol; vol = null;
                habitants = fini.IsFaulted ? (habitants.maison, Lecture<TerresDuPays>.Absent("pays : " + fini.Exception.GetBaseException().Message)) : fini.Result;
            }
            string id = montree?.Id;
            if (id == null || vol != null || habitants.maison == id || lireHabitants == null) return;
            habitants = (id, null);
            vol = Task.Run(() => (id, lireHabitants(id)));
        }

        static string Compte(long n) => TexteDuMonde.Nombre(n) + (n > 1 ? " habitants" : " habitant");

        // La ligne du pays : ses habitants à lui seul, tels que `/terres` les sert ; l'attente tant que les terres ne sont pas lues.
        string HabitantsDuPays()
        {
            var lues = terres();
            if (lues == null) return Nom() + " : habitants en lecture…";
            return Nom() + " : " + (lues.HabitantsDu(paysMontre) is long n ? Compte(n) : "habitants non servis par le monde");
        }

        // La ligne de la maison, d'après `/pays` : ses habitants avec ceux de ses vassaux, le nom de la maison devant le total qu'il compte.
        string HabitantsDeLaMaison()
        {
            string maison = montree.Nom ?? MAISON_SANS_NOM;
            string tete = montree.Nom == null ? "Maison non nommée par le monde"
                : "Maison " + DossierTerritoire.De(maison);
            if (lireHabitants == null || habitants.maison != montree.Id || habitants.lu == null) return tete + " : habitants en lecture…";
            var lu = habitants.lu;
            if (!lu.Presente) return tete + " : habitants non lus (" + TexteDuMonde.Absence(lu.Absence, montree.Id) + ")";
            if (lu.Donnees.MaisonId != montree.Id) return tete + " : habitants en lecture…";
            return tete + (lu.Donnees.VassauxTous.Count > 0 ? ", avec ses vassaux" : "") + " : " + Compte(lu.Donnees.Habitants);
        }

        void EcrireLaFiche()
        {
            if (!designe) { nom.text = AUCUN; fiche.text = INVITATION; return; }
            nom.text = Nom();
            var lignes = new List<string> { HabitantsDuPays() };
            if (montree == null)
            {
                lignes.Add("Maison : " + (maisonMontree == null ? MAISON_SANS_NOM : maisonMontree.Nom ?? MAISON_SANS_NOM));
                fiche.text = string.Join("\n", lignes);
                return;
            }
            lignes.Add(HabitantsDeLaMaison());
            var autres = montree.Regne.Where(p => p.Id != paysMontre).Select(p => p.Nom ?? SANS_NOM).ToArray();
            if (autres.Length > 0) lignes.Add("Règne aussi sur : " + string.Join(", ", autres));
            if (montree.Siege.Nom != null) lignes.Add("Siège : " + montree.Siege.Nom);
            if (montree.Suzerain != null) lignes.Add("Suzerain : " + (montree.Suzerain.Nom ?? MAISON_SANS_NOM) + (montree.Suzerain.Pays.Nom != null ? " (" + montree.Suzerain.Pays.Nom + ")" : ""));
            lignes.Add(montree.Ville.Batie ? "Ville à bâtir : oui" : "Ville à bâtir : non, pas encore de ville\n" + PhraseDeRaison(montree.Ville.Raison));
            fiche.text = string.Join("\n", lignes);
        }

        // La raison servie, en phrase : sa première lettre en capitale, un point final.
        public static string PhraseDeRaison(string raison) => char.ToUpperInvariant(raison[0]) + raison.Substring(1) + (raison.EndsWith(".") ? "" : ".");

        static void Detruire(UnityEngine.Object o) { if (Application.isPlaying) UnityEngine.Object.Destroy(o); else UnityEngine.Object.DestroyImmediate(o); }
    }
}
