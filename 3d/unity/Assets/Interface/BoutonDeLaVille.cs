using System;
using Forge.Pont;
using UnityEngine;
using UnityEngine.UI;

namespace Forge.Interface
{
    // « Entrer dans la ville », dans le bandeau entre la date et les dossiers. Visible dès qu'une maison du joueur est servie,
    // actif seulement quand sa fiche jouable dit sa capitale bâtie : un clic ouvre la scène servie sur la cellule du siège servi.
    // Grisé, son infobulle dit la raison servie. Une classe simple : le cabinet l'appelle à chaque image.
    public sealed class BoutonDeLaVille
    {
        public const string NOM = "Entrer dans la ville";
        public const string LECTURE = "Lecture de votre capitale…", HORS_CARTE = "Le siège de votre capitale n'est pas sur la carte.";
        public const float X = 888, Y = 20, LARGEUR = 216;

        readonly Button bouton;
        readonly Infobulle bulle;
        readonly Func<LecturePartie> partie;
        readonly Func<string, long, bool> entrer;
        bool maisonVue, descendu; // descendu : la ville est demandée, une seule fois

        public Button Bouton => bouton;
        public string Phrase => bulle.Phrase;
        // Le bouton répond au clic : la ville est ouvrable et la descente n'est pas déjà partie.
        public bool Actif => bouton.interactable;

        // `entrer` reçoit le nom de la scène et la cellule du siège, et dit si la descente part.
        public BoutonDeLaVille(RectTransform bandeau, Func<LecturePartie> partie, Func<string, long, bool> entrer)
        {
            this.partie = partie; this.entrer = entrer;
            bouton = SocleInterface.Commande(bandeau, NOM, X, Y, Entrer, false, LECTURE);
            bouton.GetComponent<RectTransform>().sizeDelta = new Vector2(LARGEUR, SocleInterface.HauteurCommande);
            var texte = bouton.GetComponentInChildren<Text>(); texte.rectTransform.sizeDelta = new Vector2(LARGEUR, SocleInterface.HauteurCommande); texte.supportRichText = false;
            bulle = bouton.GetComponent<Infobulle>();
            bouton.gameObject.SetActive(false);
        }

        // La descente par le passage à la capitale posé sur la carte ; sans passage, rien ne part.
        public static Func<string, long, bool> Par(GameObject carte) => (scene, cellule) =>
        {
            var passage = carte.GetComponent<PassageALaCapitale>();
            return passage != null && passage.Entrer(scene, cellule);
        };

        public void Afficher()
        {
            var lue = partie(); var monde = lue?.Monde;
            if (monde != null && monde.Presente && monde.Donnees.MaisonDuJoueur != null) maisonVue = true;
            bouton.gameObject.SetActive(maisonVue);
            if (!maisonVue) return;
            var fiche = lue?.Jouable;
            bouton.interactable = Ouvrable(fiche) && !descendu;
            bulle.phrase = fiche == null ? LECTURE : !fiche.Ville.Batie ? AccueilDuPays.PhraseDeRaison(fiche.Ville.Raison)
                : fiche.Siege.CellId == null ? HORS_CARTE : "Ouvre " + (fiche.Siege.Nom ?? "votre siège") + ", votre capitale.";
        }

        static bool Ouvrable(FicheJouable fiche) => fiche != null && fiche.Ville.Batie && fiche.Ville.NomDeScene != null && fiche.Siege.CellId != null;

        // Le geste du bouton, que l'encart des premiers gestes reprend : sans fiche ouvrable, ou déjà descendu, rien ne part.
        public void Entrer()
        {
            var fiche = partie()?.Jouable;
            if (!Ouvrable(fiche) || descendu) return;
            if (entrer(fiche.Ville.NomDeScene, fiche.Siege.CellId.Value)) { descendu = true; bouton.interactable = false; }
        }
    }
}
