using System;
using System.Collections.Generic;
using System.Linq;
using Forge.Pont;
using UnityEngine;
using UnityEngine.UI;

namespace Forge.Interface
{
    // L'encart des trois premiers gestes, en bas à gauche de la carte : lancer le temps, entrer dans sa ville, lever une armée ; et,
    // dessous, les gestes de la carte écrits en clair (glisser, zoomer, cliquer). Visible dès que le choix du pays est reçu (le monde
    // reste en pause, sa maison n'est pas encore servie) ou qu'une maison du joueur est servie, jusqu'à ce que le joueur le ferme pour cette maison. Chaque ligne dit en mots
    // quand elle est faite d'après ce que le monde sert (l'horloge lue, les armées de `/guerres`) : l'encart ne compte rien lui-même.
    // La ville reprend l'état et le clic du bouton du bandeau. L'état fermé survit au cabinet reconstruit (un aller-retour par la
    // ville détruit et refait la carte). Une classe simple : le cabinet l'appelle à chaque image.
    public sealed class PremiersGestes
    {
        public const string TITRE = "Vos premiers gestes";
        public const string TEMPS = "Lancer le temps", VILLE = "Entrer dans votre ville", ARMEE = "Lever une armée", FAIT = " : fait";
        public const string LANCER = "Lancer", ENTRER = "Entrer", LEVER = "Lever";
        public const string HORLOGE_ATTENDUE = "Le monde n'a pas encore servi son horloge : le temps ne peut pas se lancer.";
        public const string ARMEE_ATTENDUE = "Votre maison n'est pas encore servie : lancez le temps, le monde applique votre choix au jour suivant.";
        const string LEVER_L_OST = "Ouvre le feuillet de la guerre : on y lève l'ost, avec le prix de chaque ordre.";
        public const string GESTES = "Glisser : déplacer la carte · Molette : zoomer · Clic : ouvrir une terre", LIGNE_DES_GESTES = "Gestes de la carte";
        public const float X = 24, Y = 860, LARGEUR = 740, HAUTEUR = 196; // sous les feuillets (124 à 856), le bas à 1056, au-dessus de la bande des modes
        const float BORD = 24, LARGEUR_TEXTE = 508, X_BOUTON = 556, LARGEUR_BOUTON = 160, HAUTEUR_LIGNE = 30, PREMIERE_LIGNE = 76, PAS = 32, HAUTEUR_DES_GESTES = 22;

        static readonly HashSet<string> fermes = new HashSet<string>(); // les maisons dont le joueur a fermé l'encart

        readonly RectTransform panneau;
        readonly Button temps, entrer, armee, fermer;
        readonly Text[] textes = new Text[3];
        readonly Text gestes;
        readonly Infobulle bulleDuTemps, bulleDeLaVille, bulleDeLArmee;
        readonly Func<LecturePartie> partie;
        readonly Func<HorlogeLue> horloge;
        readonly BoutonDeLaVille boutonDeLaVille;
        readonly Func<GuerresLues> guerres;
        string maison; // la maison du joueur une fois servie ; la coupure du monde ne la retire pas
        bool fermeAvantLaMaison; // fermé entre le choix reçu et la maison servie : il le reste pour elle
        readonly bool[] faites = new bool[3];

        public RectTransform Panneau => panneau;
        public Button BoutonTemps => temps;
        public Button BoutonVille => entrer;
        public Button BoutonArmee => armee;
        public Button BoutonFermer => fermer;
        public bool Visible => panneau.gameObject.activeSelf;
        // Le texte écrit de la ligne 0 (le temps), 1 (la ville) ou 2 (l'armée).
        public string Texte(int ligne) => textes[ligne].text;
        public string TexteDesGestes => gestes.text;
        // Une ligne faite : le temps file, l'armée de la maison est servie. La ville n'a pas d'état fait : son bouton dit si elle s'ouvre.
        public bool Faite(int ligne) => faites[ligne];

        // `lancerLeTemps` bascule l'horloge ; `leverUneArmee` ouvre le feuillet de la guerre ; `guerres` donne les guerres lues (nul tant qu'elles ne le sont pas).
        public PremiersGestes(Transform toile, Func<LecturePartie> partie, Func<HorlogeLue> horloge, Action lancerLeTemps, BoutonDeLaVille ville,
            Action leverUneArmee, Func<GuerresLues> guerres)
        {
            this.partie = partie; this.horloge = horloge; this.boutonDeLaVille = ville; this.guerres = guerres;
            panneau = SocleInterface.Panneau(toile, TITRE, X, Y, LARGEUR, HAUTEUR);
            fermer = SocleInterface.Croix(panneau, Fermer, "Ferme cet encart pour votre maison ; il ne revient pas.");
            temps = Ligne(0, TEMPS, LANCER, lancerLeTemps, "Lance le temps du monde, ou l'arrête s'il court déjà.");
            entrer = Ligne(1, VILLE, ENTRER, ville.Entrer, "Ouvre votre capitale.");
            armee = Ligne(2, ARMEE, LEVER, leverUneArmee, LEVER_L_OST);
            gestes = SocleInterface.Texte(panneau, GESTES, BORD, PREMIERE_LIGNE + 3 * PAS, LARGEUR - 2 * BORD); gestes.name = LIGNE_DES_GESTES;
            gestes.rectTransform.sizeDelta = new Vector2(LARGEUR - 2 * BORD, HAUTEUR_DES_GESTES); gestes.alignment = TextAnchor.MiddleLeft; gestes.verticalOverflow = VerticalWrapMode.Overflow; gestes.color = SocleInterface.Couleur("secondaire");
            bulleDuTemps = temps.GetComponent<Infobulle>(); bulleDeLaVille = entrer.GetComponent<Infobulle>(); bulleDeLArmee = armee.GetComponent<Infobulle>();
            foreach (var texte in panneau.GetComponentsInChildren<Text>(true)) texte.supportRichText = false;
            panneau.gameObject.SetActive(false);
        }

        Button Ligne(int rang, string phrase, string nom, Action action, string aide)
        {
            float y = PREMIERE_LIGNE + rang * PAS;
            var texte = SocleInterface.Texte(panneau, phrase, BORD, y, LARGEUR_TEXTE);
            texte.rectTransform.sizeDelta = new Vector2(LARGEUR_TEXTE, HAUTEUR_LIGNE); texte.alignment = TextAnchor.MiddleLeft; textes[rang] = texte;
            var bouton = SocleInterface.Commande(panneau, nom, X_BOUTON, y, action, phrase: aide);
            bouton.GetComponent<RectTransform>().sizeDelta = new Vector2(LARGEUR_BOUTON, HAUTEUR_LIGNE);
            bouton.GetComponentInChildren<Text>().rectTransform.sizeDelta = new Vector2(LARGEUR_BOUTON, HAUTEUR_LIGNE);
            return bouton;
        }

        public void Afficher()
        {
            var lue = partie(); var monde = lue?.Monde;
            if (monde != null && monde.Presente && monde.Donnees.MaisonDuJoueur != null) maison = monde.Donnees.MaisonDuJoueur;
            if (maison != null && fermeAvantLaMaison) { fermes.Add(maison); fermeAvantLaMaison = false; }
            bool visible = maison != null ? !fermes.Contains(maison) : lue?.Recu?.Acceptee == true && !fermeAvantLaMaison;
            panneau.gameObject.SetActive(visible);
            if (!visible) return;
            var lu = horloge();
            faites[0] = lu != null && lu.JoursParSeconde > 0;
            faites[1] = false;
            var lues = guerres();
            faites[2] = lues != null && lues.Armees.Any(a => a.Maison == maison);
            Ecrire(0, TEMPS); Ecrire(1, VILLE); Ecrire(2, ARMEE);
            temps.interactable = lu != null;
            bulleDuTemps.phrase = lu == null ? HORLOGE_ATTENDUE : lu.JoursParSeconde > 0 ? "Arrête le temps du monde ; le même bouton le relance." : "Lance le temps du monde à la vitesse choisie.";
            entrer.interactable = boutonDeLaVille.Actif;
            bulleDeLaVille.phrase = boutonDeLaVille.Phrase; // grisé, la raison servie du bouton du bandeau
            armee.interactable = maison != null; // le choix reçu n'a pas encore de maison : l'ost se lève quand le monde l'a servie
            bulleDeLArmee.phrase = maison != null ? LEVER_L_OST : ARMEE_ATTENDUE;
        }

        void Ecrire(int rang, string phrase) => textes[rang].text = faites[rang] ? phrase + FAIT : phrase;

        // Ferme l'encart pour cette maison, jusqu'à la fin de la partie jouée.
        void Fermer()
        {
            if (maison != null) fermes.Add(maison); else fermeAvantLaMaison = true;
            panneau.gameObject.SetActive(false);
        }

        // Vide l'état fermé : un test repart d'un encart ouvert.
        public static void OublierLesFermetures() => fermes.Clear();
    }
}
