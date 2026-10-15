using System;
using System.Globalization;
using UnityEngine;
using UnityEngine.UI;

namespace Forge.Interface
{
    public enum EtatLecture { Attente, Absence, Refus, Panne }

    public static class EtatsLecture
    {
        public static void Afficher(Text texte, EtatLecture etat, string cause)
        {
            string titre, couleur;
            switch (etat)
            {
                case EtatLecture.Attente: titre = "… En attente"; couleur = "accent"; break;
                case EtatLecture.Absence: titre = "— Donnée absente"; couleur = "secondaire"; break;
                case EtatLecture.Refus: titre = "× Demande refusée"; couleur = "alerte"; break;
                case EtatLecture.Panne: titre = "! Le monde ne répond pas"; couleur = "alerte"; break;
                default: throw new ArgumentOutOfRangeException(nameof(etat));
            }
            Exiger(cause, nameof(cause));
            Ecrire(texte, titre + "\n" + cause, couleur);
        }

        public static void Mesure(Text texte, decimal? valeur, string unite)
        {
            Exiger(unite, nameof(unite));
            if (!valeur.HasValue)
            {
                Afficher(texte, EtatLecture.Absence, "La source ne fournit pas cette quantité.");
                return;
            }
            var nombre = valeur.Value.ToString("0.############################", CultureInfo.GetCultureInfo("fr-FR"));
            Ecrire(texte, nombre + " " + unite, "encre");
        }

        static void Exiger(string contenu, string nom)
        {
            if (string.IsNullOrWhiteSpace(contenu)) throw new ArgumentException("Information absente : " + nom, nom);
        }

        static void Ecrire(Text texte, string contenu, string couleur)
        {
            texte.supportRichText = false;
            texte.text = contenu;
            texte.color = SocleInterface.Couleur(couleur);
            texte.rectTransform.SetSizeWithCurrentAnchors(RectTransform.Axis.Vertical, texte.preferredHeight);
        }
    }
}
