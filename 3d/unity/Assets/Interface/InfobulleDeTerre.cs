using System; using Forge.Pont; using UnityEngine; using UnityEngine.InputSystem; using UnityEngine.UI;

namespace Forge.Interface
{
    // Lot #880 : près du curseur, les trois premières lignes du dossier de la terre survolée. LateUpdate suit SurvolDeCarte.
    public sealed class InfobulleDeTerre : MonoBehaviour
    {
        public const int LIGNES = 3; public const double PERIODE_S = 2;
        public bool automatique; public LectureDossier Lecture { get; set; } public string TexteAffiche { get; private set; }
        Canvas toile; Func<CelluleDeCarte> survolee; double prochaine; long? cellule; DocumentDuMonde document; string erreur, texte;

        public static string Decrire(string erreur, DocumentDuMonde document, long cellule)
        { var lignes = DossierTerritoire.Texte(erreur, document, cellule).Split('\n'); return lignes.Length < LIGNES ? lignes[0] : string.Join("\n", lignes, 0, LIGNES); }
        public void Initialiser(Canvas toile, LectureDossier lecture, Func<CelluleDeCarte> survolee) { this.toile = toile; Lecture = lecture; this.survolee = survolee; }

        public void Pas(Vector2 point, CelluleDeCarte terre, double maintenant)
        {
            if (terre == null)
            {
                var feuillet = TexteAffiche != null ? toile.transform.Find("Infobulle") : null;
                var ecrit = feuillet != null && feuillet.gameObject.activeInHierarchy ? feuillet.GetComponentInChildren<Text>(true) : null;
                if (ecrit != null && ecrit.text == TexteAffiche) Infobulle.Cacher(toile);
                TexteAffiche = null; return;
            }
            string chemin = "/lieu?cell=" + terre.CellId;
            if (!Lecture.EnCours && (Lecture.Cle != chemin || maintenant >= prochaine)) { _ = Lecture.Actualiser(chemin); prochaine = maintenant + PERIODE_S; }
            bool meme = Lecture.Cle == chemin; var lu = meme ? Lecture.Document : null; string faute = meme ? Lecture.Erreur : null;
            if (cellule != terre.CellId || document != lu || erreur != faute) { cellule = terre.CellId; document = lu; erreur = faute; texte = Decrire(faute, lu, terre.CellId); }
            TexteAffiche = texte; Infobulle.Montrer(toile, TexteAffiche, point);
        }

        void LateUpdate() { if (automatique || Mouse.current == null) return; Pas(Mouse.current.position.ReadValue(), survolee(), Time.realtimeSinceStartupAsDouble); }
    }
}
