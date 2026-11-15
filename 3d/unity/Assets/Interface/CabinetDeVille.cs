using System;
using System.Linq;
using System.Text;
using Forge.Pont;
using UnityEngine;
using UnityEngine.UI;

namespace Forge.Interface
{
    // Le cabinet de la ville du désert : deux feuillets du socle posés sur l'image de la caméra de la ville.
    // « Le bourg » écrit pour le joueur la dernière lecture du lieu que fait PanneauLieu ; « Outils de la
    // ville » écrit l'aide du tracé. Rien ici n'est lu au service ni calculé : chaque image relit ce que
    // PanneauLieu et l'outil ont déjà reçu. La toile est rendue par la caméra de la ville, donc elle
    // entre dans ses photos. Les textes ne montrent ni identifiant, ni mot de mise au point, ni nombre sans unité.
    public sealed class CabinetDeVille : MonoBehaviour
    {
        public const string BOURG = "Le bourg";
        public const string OUTILS = "Outils de la ville";
        public const string ATTENTE = "Le bourg attend le monde.";
        public const string SANS_NOM = "Bourg sans nom";
        const string NOURRITURE = "nourriture";
        const string OUVRIERS = "ouvriers";
        const float ECART_PLAN = 0.2f; // derrière le plan proche : rien de la scène ne passe devant les feuillets
        const float MARGE = 24f, HAUT_TEXTE = 88f; // sous le titre et son filet, comme les autres feuillets du socle
        const float LARGEUR_BOURG = 560f, LARGEUR_OUTILS = 760f;

        public Canvas Toile { get; private set; }
        public RectTransform FeuilletDuBourg { get; private set; }
        public RectTransform FeuilletDesOutils { get; private set; }
        public string TexteDuBourg => texteBourg != null ? texteBourg.text : null;
        public string TexteDesOutils => texteOutils != null ? texteOutils.text : null;

        Text texteBourg, texteOutils;
        PanneauLieu panneauLieu;
        Func<string> outils;
        LectureLieu bourgEcrit;
        bool bourgDejaEcrit;

        // La caméra qui rend la toile ; le panneau du lieu et le texte des outils peuvent manquer (la scène de l'oued n'a pas de panneau).
        public void Initialiser(Camera camera, PanneauLieu lieu, Func<string> texteDesOutils)
        {
            if (camera == null) throw new ArgumentNullException(nameof(camera));
            if (Toile != null) return;
            panneauLieu = lieu;
            outils = texteDesOutils;

            var racine = new GameObject("Cabinet de la ville", typeof(RectTransform), typeof(Canvas), typeof(CanvasScaler));
            racine.transform.SetParent(transform, false);
            Toile = racine.GetComponent<Canvas>();
            Toile.renderMode = RenderMode.ScreenSpaceCamera;
            Toile.worldCamera = camera;
            Toile.planeDistance = camera.nearClipPlane + ECART_PLAN;
            var echelle = racine.GetComponent<CanvasScaler>();
            echelle.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
            echelle.referenceResolution = new Vector2(1920, 1080);

            FeuilletDuBourg = SocleInterface.Panneau(racine.transform, BOURG, MARGE, MARGE, LARGEUR_BOURG, 200);
            texteBourg = SocleInterface.Texte(FeuilletDuBourg, "", MARGE, HAUT_TEXTE, LARGEUR_BOURG - 2 * MARGE);
            texteBourg.name = "Texte du bourg";

            // Les outils s'ancrent en bas à gauche : la hauteur de l'image ne les déplace pas.
            FeuilletDesOutils = SocleInterface.Panneau(racine.transform, OUTILS, MARGE, MARGE, LARGEUR_OUTILS, 200);
            FeuilletDesOutils.anchorMin = FeuilletDesOutils.anchorMax = FeuilletDesOutils.pivot = Vector2.zero;
            FeuilletDesOutils.anchoredPosition = new Vector2(MARGE, MARGE);
            texteOutils = SocleInterface.Texte(FeuilletDesOutils, "", MARGE, HAUT_TEXTE, LARGEUR_OUTILS - 2 * MARGE);
            texteOutils.name = "Texte des outils";

            foreach (var texte in racine.GetComponentsInChildren<Text>()) texte.supportRichText = false;
            EcrireLeBourg(null);
            EcrireLesOutils(outils?.Invoke());
        }

        void LateUpdate()
        {
            if (Toile == null) return;
            LectureLieu lecture = panneauLieu != null ? panneauLieu.DerniereLecture : null;
            if (!bourgDejaEcrit || !ReferenceEquals(lecture, bourgEcrit)) EcrireLeBourg(lecture);
            EcrireLesOutils(outils?.Invoke());
        }

        void EcrireLeBourg(LectureLieu lecture)
        {
            bourgDejaEcrit = true;
            bourgEcrit = lecture;
            if (lecture == null) EtatsLecture.Afficher(texteBourg, EtatLecture.Attente, ATTENTE);
            else if (!lecture.Presente) EtatsLecture.Afficher(texteBourg, EtatLecture.Panne, TexteDuMonde.Absence(lecture.Absence));
            else
            {
                try
                {
                    string texte = Decrire(lecture.Lieu);
                    texteBourg.text = texte;
                    texteBourg.color = SocleInterface.Couleur("encre");
                }
                catch (ArgumentException e) // une date que le monde n'aurait pas dû servir : dite, jamais lue de travers
                {
                    EtatsLecture.Afficher(texteBourg, EtatLecture.Panne, TexteDuMonde.Absence("le lieu servi est illisible : " + e.Message));
                }
            }
            Ajuster(FeuilletDuBourg, texteBourg);
        }

        void EcrireLesOutils(string texte)
        {
            texte = texte ?? "";
            FeuilletDesOutils.gameObject.SetActive(texte.Length > 0);
            if (texteOutils.text == texte) return;
            texteOutils.text = texte;
            texteOutils.color = SocleInterface.Couleur("encre");
            Ajuster(FeuilletDesOutils, texteOutils);
        }

        // Le feuillet suit la hauteur de son texte, sous le titre et son filet.
        static void Ajuster(RectTransform feuillet, Text texte)
        {
            SocleInterface.Ajuster(texte);
            feuillet.SetSizeWithCurrentAnchors(RectTransform.Axis.Vertical, HAUT_TEXTE + texte.rectTransform.rect.height + MARGE);
        }

        // Le texte du feuillet « Le bourg », écrit pour le joueur : des noms, des dates, des masses et des durées avec
        // leur unité, aucune cellule ni aucun rang. Ce que le service dit « non calculé » s'écrit tel quel, jamais zéro.
        public static string Decrire(Lieu lieu)
        {
            if (lieu == null) throw new ArgumentNullException(nameof(lieu));
            var s = new StringBuilder();
            s.Append(lieu.Bourg?.Nom ?? SANS_NOM).Append(" · ").Append(TexteDuMonde.Date(new DateDuMonde(lieu.Annee, lieu.JourDeLAnnee))).Append('\n');
            s.Append("Habitants : ").Append(TexteDuMonde.Nombre(lieu.Population)).Append(lieu.Population > 1 ? " habitants" : " habitant").Append('\n');
            s.Append("Nourriture : ").Append(lieu.Stocks.TryGetValue(NOURRITURE, out double kg) ? TexteDuMonde.Masse(kg) : "absente du grenier").Append('\n');
            foreach (var marchandise in lieu.Stocks.Where(m => m.Key != NOURRITURE).OrderBy(m => m.Key, StringComparer.Ordinal))
                s.Append(marchandise.Key).Append(" : ").Append(TexteDuMonde.Masse(marchandise.Value)).Append('\n');
            // La faim est une durée en jours de manque (un tick est un jour) ; -1 dit « non calculée ».
            s.Append("Faim : ").Append(lieu.HungerTicks < 0 ? "non calculée" : lieu.HungerTicks == 0 ? "aucune" : TexteDuMonde.Jours(lieu.HungerTicks) + " de manque").Append('\n');
            s.Append("Dette de nourriture : ").Append(lieu.FoodDeficitKg < 0 ? "non calculée" : TexteDuMonde.Masse(lieu.FoodDeficitKg));
            s.Append('\n').Append(DecrireLesFoyers(lieu));
            return s.ToString();
        }

        // Foyers, chantier et logement, lus tels quels : aucune somme, aucune division.
        static string DecrireLesFoyers(Lieu lieu)
        {
            var s = new StringBuilder("Foyers par métier :");
            if (lieu.EtatFoyers == EtatFoyers.Servis && lieu.Foyers.Count > 0)
                foreach (var metier in lieu.Foyers)
                    s.Append('\n').Append(metier.Key).Append(" : ").Append(Compter(metier.Value.Foyers, "foyer", "foyers"))
                        .Append(", ").Append(Compter(metier.Value.Personnes, "personne", "personnes"));
            else s.Append(lieu.EtatFoyers == EtatFoyers.Servis ? " aucun"
                : lieu.EtatFoyers == EtatFoyers.NonCalcules ? " non calculés par le monde" : " absents de la réponse du service");
            s.Append("\nAu chantier : ").Append(lieu.EtatFoyers == EtatFoyers.NonCalcules ? "non calculé"
                : lieu.EtatFoyers == EtatFoyers.Absents ? "absent de la réponse du service"
                : lieu.Foyers.TryGetValue(OUVRIERS, out var ouvriers) ? TexteDuMonde.Nombre(ouvriers.Personnes) + " bras pris aux champs" : "personne");
            Logement l = lieu.Logement;
            if (l == null) s.Append("\nLogement : absent du service (aucun bâtiment au plan)");
            else if (l.Loges == -1 || l.SansLogis == -1)
                s.Append("\nLogement des artisans : capacité de ").Append(Compter(l.Capacite, "foyer", "foyers")).Append(", logés et sans-logis non calculés");
            else s.Append("\nLogement des artisans : ").Append(Compter(l.Loges, "foyer logé", "foyers logés")).Append(", ")
                .Append(Compter(l.SansLogis, "foyer sans logis", "foyers sans logis")).Append(", capacité de ").Append(Compter(l.Capacite, "foyer", "foyers"));
            return s.ToString();
        }

        static string Compter(long n, string un, string plusieurs) => TexteDuMonde.Nombre(n) + " " + (n > 1 ? plusieurs : un);
    }
}
