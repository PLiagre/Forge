using System; using System.Collections.Generic; using System.Linq; using Forge.Pont; using UnityEngine; using UnityEngine.InputSystem; using UnityEngine.UI;

namespace Forge.Interface
{
    // Lot #880 : près du curseur, les trois premières lignes du dossier de la terre survolée. LateUpdate suit SurvolDeCarte.
    // Lot #1031 : puis, du registre `/modificateurs` lu au même tick, une ligne par modificateur du bourg et le total de chaque grandeur, tels que le monde les sert.
    public sealed class InfobulleDeTerre : MonoBehaviour
    {
        public const int LIGNES = 3; public const double PERIODE_S = 2; public const string CHEMIN_MODIFICATEURS = "/modificateurs"; public const string SANS_FIN = "tant que sa source tient";
        public bool automatique; public LectureDossier Lecture { get; set; } public LectureDossier LectureModificateurs { get; set; } public string TexteAffiche { get; private set; }
        Canvas toile; Func<CelluleDeCarte> survolee; double prochaine, prochaineModificateurs; long? cellule; DocumentDuMonde document, registre; string erreur, erreurRegistre, texte;

        public static string Decrire(string erreur, DocumentDuMonde document, long cellule)
        { var lignes = DossierTerritoire.Texte(erreur, document, cellule).Split('\n'); return lignes.Length < LIGNES ? lignes[0] : string.Join("\n", lignes, 0, LIGNES); }

        // Les lignes du bourg (rang 0) de la terre, dans l'ordre servi : une par pose, puis le total de sa grandeur. Rien n'est additionné ici ; vide si le bourg n'a pas de pose.
        public static string[] DecrireModificateurs(DocumentDuMonde modificateurs, long cellule)
        {
            var dites = new List<string>();
            var bourg = DocumentDuMonde.Tableau(modificateurs.Champs, "lieux").Select(l => l as Dictionary<string, object> ?? throw new ArgumentException("Lieu illisible")).FirstOrDefault(l => DocumentDuMonde.Entier(l, "cell_id") == cellule && DocumentDuMonde.Entier(l, "rang") == 0);
            if (bourg == null) return dites.ToArray();
            foreach (var paire in DocumentDuMonde.Objet(bourg, "grandeurs"))
            {
                var grandeur = paire.Value as Dictionary<string, object> ?? throw new ArgumentException("Grandeur illisible : " + paire.Key); string nom = DocumentDuMonde.Texte(grandeur, "nom");
                foreach (Dictionary<string, object> ligne in DocumentDuMonde.Tableau(grandeur, "lignes").Select(l => l as Dictionary<string, object> ?? throw new ArgumentException("Ligne illisible : " + paire.Key)))
                {
                    object reste = DocumentDuMonde.Valeur(ligne, "reste_jours");
                    string duree = reste == null ? SANS_FIN : "encore " + TexteDuMonde.Jours(DocumentDuMonde.Entier(ligne, "reste_jours"));
                    dites.Add(nom + " : " + TexteDuMonde.Pourcentage(DocumentDuMonde.Nombre(ligne, "valeur")) + " " + DocumentDuMonde.Texte(ligne, "nom") + " · " + DocumentDuMonde.Texte(ligne, "source_dite") + " · " + duree);
                }
                dites.Add(nom + ", total : " + TexteDuMonde.Pourcentage(DocumentDuMonde.Nombre(grandeur, "total")));
            }
            return dites.ToArray();
        }

        // Le texte montré : les lignes du dossier, et celles des modificateurs seulement s'ils sont lus, sans faute, au tick de ce dossier ; sinon le texte d'avant le lot, au caractère près.
        static string Montrer(string erreur, DocumentDuMonde dossier, DocumentDuMonde registre, string erreurRegistre, long cellule)
        {
            string base3 = Decrire(erreur, dossier, cellule);
            if (erreur != null || dossier == null || registre == null || erreurRegistre != null || registre.Tick != dossier.Tick) return base3;
            try { var lignes = DecrireModificateurs(registre, cellule); return lignes.Length == 0 ? base3 : base3 + "\n" + string.Join("\n", lignes); }
            catch (ArgumentException faute) { Debug.LogWarning("InfobulleDeTerre : modificateurs illisibles, ignorés : " + faute.Message); return base3; }
        }

        public void Initialiser(Canvas toile, LectureDossier lecture, Func<CelluleDeCarte> survolee, LectureDossier modificateurs = null) { this.toile = toile; Lecture = lecture; LectureModificateurs = modificateurs; this.survolee = survolee; }

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
            var modificateurs = LectureModificateurs;
            if (modificateurs != null && !modificateurs.EnCours && (modificateurs.Cle != CHEMIN_MODIFICATEURS || maintenant >= prochaineModificateurs)) { _ = modificateurs.Actualiser(CHEMIN_MODIFICATEURS); prochaineModificateurs = maintenant + PERIODE_S; }
            bool meme = Lecture.Cle == chemin; var lu = meme ? Lecture.Document : null; string faute = meme ? Lecture.Erreur : null;
            var registreLu = modificateurs?.Cle == CHEMIN_MODIFICATEURS ? modificateurs.Document : null; string fauteRegistre = modificateurs?.Cle == CHEMIN_MODIFICATEURS ? modificateurs.Erreur : null;
            if (cellule != terre.CellId || document != lu || erreur != faute || registre != registreLu || erreurRegistre != fauteRegistre)
            { cellule = terre.CellId; document = lu; erreur = faute; registre = registreLu; erreurRegistre = fauteRegistre; texte = Montrer(faute, lu, registreLu, fauteRegistre, terre.CellId); }
            TexteAffiche = texte; Infobulle.Montrer(toile, TexteAffiche, point);
        }

        void LateUpdate() { if (automatique || Mouse.current == null) return; Pas(Mouse.current.position.ReadValue(), survolee(), Time.realtimeSinceStartupAsDouble); }
    }
}
