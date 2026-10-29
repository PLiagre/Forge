using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;

namespace Forge.Interface
{
    public sealed class OutilRue : MonoBehaviour
    {
        DossierBourg dossier;
        DessinBourg dessin;
        Text legende, message;
        Transform commandes;
        InputField largeur, foyers;
        Button ouvrir, preparer, confirmer, annuler;
        readonly List<Vector2> points = new List<Vector2>();
        public OrdreConfirme Ordre { get; private set; }
        bool edition;
        long cible;
        string maisonCible, erreur;
        string Maison => dossier.GetComponent<CabinetDeCarte>().Partie.Maison?.Presente == true
            ? dossier.GetComponent<CabinetDeCarte>().Partie.Maison.Donnees.Id : null;
        bool Permis()
        {
            try { return dossier.Document != null && OrdreRue.Permis(dossier.GetComponent<DossierTerritoire>().Document, dossier.Cellule, Maison); }
            catch (Exception) { return false; }
        }
        bool MemeContexte() => Permis() && cible == dossier.Cellule && maisonCible == Maison;
        public void Initialiser(DossierBourg dossier, DessinBourg dessin, Text legende, int port)
        {
            this.dossier = dossier; this.dessin = dessin; this.legende = legende; Ordre = OrdreConfirme.Local(port);
            ouvrir = Bouton(transform, "Tracer une rue", 650, 20, 320, () =>
            {
                if (!Permis()) return;
                cible = dossier.Cellule; maisonCible = Maison; erreur = null; Mode(true);
            }, "Commence le tracé d'une rue sur le plan, sur vos terres seulement.");
            commandes = new GameObject("Préparer une rue", typeof(RectTransform)).transform; commandes.SetParent(transform, false);
            var cadre = (RectTransform)commandes; cadre.anchorMin = cadre.anchorMax = cadre.pivot = new Vector2(0, 1);
            cadre.anchoredPosition = new Vector2(24, -528);
            largeur = Saisie("Largeur (m)", 0, "6"); foyers = Saisie("Foyers", 310, "1");
            preparer = Bouton(commandes, "Relire le tracé", 650, 0, 240, Preparer, "Prépare la rue tracée, sans l'envoyer ; le monde en calculera le coût.");
            annuler = Bouton(commandes, "Annuler / Retour", 926, 0, 264, () =>
            { if (Ordre.Recommencer()) { points.Clear(); erreur = null; Mode(false); } }, "Abandonne le tracé et revient au plan ; rien n'est envoyé.");
            message = SocleInterface.Texte(commandes, "", 0, 56, 1190);
            confirmer = Bouton(commandes, "Confirmer la rue", 650, 116, 240, () => { if (MemeContexte()) _ = Ordre.Confirmer(); }, "Envoie la rue au monde ; il l'applique au jour suivant.");
            MatieresCabinet.Engagement(confirmer);
            dessin.Pointer = p =>
            {
                if (!edition || !MemeContexte() || Ordre.Brouillon != null || Ordre.EnCours || Ordre.Recu != null) return;
                points.Add(p); erreur = null; dessin.Esquisser(points.ToArray());
            };
            Mode(false);
        }
        InputField Saisie(string titre, float x, string valeur)
        {
            SocleInterface.Texte(commandes, titre, x, 12, 130);
            var champ = new GameObject(titre, typeof(RectTransform), typeof(Image), typeof(InputField)).GetComponent<RectTransform>();
            champ.SetParent(commandes, false); champ.anchorMin = champ.anchorMax = champ.pivot = new Vector2(0, 1);
            champ.anchoredPosition = new Vector2(x + 140, 0); champ.sizeDelta = new Vector2(130, 44);
            var saisie = champ.GetComponent<InputField>(); saisie.characterLimit = 12;
            saisie.textComponent = SocleInterface.Texte(champ, "", 8, 10, 114); saisie.text = valeur;
            return saisie;
        }
        static Button Bouton(Transform parent, string nom, float x, float y, float largeur, Action action, string phrase)
        {
            var bouton = SocleInterface.Commande(parent, nom, x, y, action, phrase: phrase);
            bouton.GetComponent<RectTransform>().sizeDelta = new Vector2(largeur, 44);
            bouton.GetComponentInChildren<Text>().rectTransform.sizeDelta = new Vector2(largeur, 44);
            return bouton;
        }
        void Mode(bool actif)
        {
            edition = actif; commandes.gameObject.SetActive(actif); legende.gameObject.SetActive(!actif);
            ouvrir.gameObject.SetActive(!actif); dessin.raycastTarget = actif;
            dessin.rectTransform.sizeDelta = new Vector2(1190, actif ? 360 : 510);
            if (!actif) dessin.Esquisser(Array.Empty<Vector2>());
        }
        void Preparer()
        {
            if (!MemeContexte()) return;
            try
            {
                Ordre.Preparer(OrdreRue.Creer(maisonCible, cible, points.ToArray(), largeur.text, foyers.text),
                    "Pointillés : tracé préparé · Territoire " + cible + " · " + points.Count + " points · largeur " + largeur.text + " m · Foyers : " + foyers.text + ". Coût calculé par le monde.");
                erreur = null;
            }
            catch (Exception e) { erreur = e.Message; }
        }
        void LateUpdate()
        {
            if (Ordre == null) return;
            ouvrir.interactable = Permis();
            if (!edition) return;
            bool contexte = MemeContexte();
            if (!contexte && !Ordre.EnCours && Ordre.Recu == null)
            { Ordre.Annuler(); points.Clear(); Mode(false); return; }
            bool modifiable = contexte && Ordre.Brouillon == null && !Ordre.EnCours && Ordre.Recu == null;
            largeur.interactable = foyers.interactable = modifiable;
            preparer.interactable = modifiable && points.Count >= 2;
            annuler.interactable = !Ordre.EnCours;
            confirmer.gameObject.SetActive(Ordre.Brouillon != null);
            confirmer.interactable = contexte && !Ordre.EnCours && Ordre.Recu == null;
            var recu = Ordre.Recu;
            message.text = recu != null ? !recu.Presente ? "Reçu inconnu : " + recu.Absence + ". Vérifiez le plan avant toute nouvelle demande."
                : recu.Acceptee ? "Rue reçue pour le territoire " + cible + ", application annoncée au tick " + recu.AppliqueeAuTick + ". Relisez le plan ; ce reçu ne signifie pas chantier terminé."
                : "Rue refusée : " + recu.Erreur
                : Ordre.EnCours ? "Envoi du tracé en cours…" : erreur ?? Ordre.Resume ?? "Cliquez sur le plan pour placer les points : " + points.Count + ". Les pointillés sont votre brouillon. Relisez avant de confirmer.";
        }
        void OnDisable()
        {
            if (Ordre == null || Ordre.EnCours || Ordre.Recu != null) return;
            Ordre.Annuler(); points.Clear(); Mode(false);
        }
    }
}
