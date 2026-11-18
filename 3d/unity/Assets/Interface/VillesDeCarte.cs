using System;
using System.Collections.Generic;
using Forge.Pont;
using UnityEngine;
using UnityEngine.Rendering;

namespace Forge.Interface
{
    // Les villes que la carte sert, chacune une figurine posée sur le sol à sa place : un bourg, une ville dans ses
    // remparts ou une cité à tours, selon ses habitants servis, sur une échelle logarithmique entre la moins et la
    // plus peuplée des villes servies. Son socle est clair, bordé d'encre, comme le rond d'une ville sur un atlas, et
    // ses toits sont au cuivre du socle. Rien d'autre ne se lit dans la figurine : ni maître, ni richesse. De loin, une
    // figurine ne descend jamais sous `MIN_PX` pixels de large ; et le nom de la ville, posé par la carte, se range
    // juste au sud d'elle, à `MARGE_DU_NOM_PX` pixels de son socle. Quand la vue recule et que deux figurines se
    // recouvriraient à l'écran de plus de `RECOUVREMENT`, la moins peuplée des deux se cache, avec son nom, et
    // revient quand la vue s'approche.
    public sealed class VillesDeCarte : MonoBehaviour
    {
        public const string RACINE = "Figurines des villes", NOMS = "Villes de la carte";
        public const float MIN_PX = 16f, MARGE_DU_NOM_PX = 11f, RECOUVREMENT = 0.25f;
        CarteDessinee carte; Transform racine; Material matiere; readonly Mesh[] formes = new Mesh[FormesDeCarte.TAILLE_MAX + 1];
        readonly List<Posee> posees = new List<Posee>(); readonly List<UnityEngine.Object> crees = new List<UnityEngine.Object>();
        sealed class Posee { public Transform Figurine, Nom; public Vector3 Pied; public int Taille; public long Habitants; public Vector2 Ecran; public float RayonPx; public bool Montree; }

        public int Posees => posees.Count;
        public int Montrees { get; private set; }
        public void Installer() { carte = GetComponent<CarteDessinee>(); }
        void LateUpdate() => Pas();
        void OnDestroy() { foreach (var o in crees) Detruire(o); crees.Clear(); posees.Clear(); }

        // La taille de la figurine d'une ville de ce nombre d'habitants, de 1 à `TAILLE_MAX`, entre la moins et la plus
        // peuplée des villes servies, sur une échelle logarithmique ; celle du milieu quand toutes ont les mêmes habitants.
        public static int Taille(long habitants, long moins, long plus)
        {
            if (plus <= moins) return 2;
            // De combien de fois la ville dépasse la moins peuplée, rapporté à ce dont la plus peuplée la dépasse.
            double bas = Math.Max(1d, moins), place = Math.Log(Math.Max(1d, habitants) / bas) / Math.Log(Math.Max(1d, plus) / bas);
            return 1 + Math.Min(FormesDeCarte.TAILLE_MAX - 1, (int)(FormesDeCarte.TAILLE_MAX * Math.Min(1d, Math.Max(0d, place))));
        }

        // Pose les figurines une fois la carte posée, puis les règle sur la vue à chaque image.
        public void Pas()
        {
            if (carte == null) return;
            if (racine == null) { if (carte.Lue == null || carte.CellulesPosees == 0) return; Poser(); }
            Camera camera = carte.camera; if (camera == null) return;
            foreach (Posee p in posees)
            {
                if (p.Figurine == null) continue;
                Vector3 monde = carte.transform.TransformPoint(p.Pied); float rayon = FormesDeCarte.RayonDuBourg(p.Taille), echelle = FormesDeCarte.EchellePourLEcran(camera, monde, rayon, MIN_PX);
                p.Figurine.localScale = Vector3.one * echelle; float kmParPixel = FormesDeCarte.KmParPixel(camera, monde);
                if (p.Nom != null) { float retrait = rayon * echelle + MARGE_DU_NOM_PX * kmParPixel; p.Nom.localPosition = carte.SurLeSol(p.Pied.x, p.Pied.z - retrait, CarteDessinee.HAUTEUR_NOM); }
                p.Ecran = camera.WorldToScreenPoint(monde); p.RayonPx = kmParPixel > 0f ? rayon * echelle / kmParPixel : 0f;
            }
            // De la plus peuplée à la moins peuplée : une figurine se montre si elle n'en recouvre aucune déjà montrée.
            Montrees = 0;
            for (int k = 0; k < posees.Count; k++)
            {
                Posee p = posees[k]; if (p.Figurine == null) continue;
                bool libre = true;
                for (int j = 0; j < k && libre; j++) { Posee q = posees[j]; if (q.Montree && (p.Ecran - q.Ecran).magnitude < (1f - RECOUVREMENT) * (p.RayonPx + q.RayonPx)) libre = false; }
                p.Montree = libre; if (libre) Montrees++;
                if (p.Figurine.gameObject.activeSelf != libre) p.Figurine.gameObject.SetActive(libre);
                if (p.Nom != null && p.Nom.gameObject.activeSelf != libre) p.Nom.gameObject.SetActive(libre);
            }
        }

        void Poser()
        {
            racine = new GameObject(RACINE).transform; racine.SetParent(transform, false); crees.Add(racine.gameObject);
            long moins = long.MaxValue, plus = long.MinValue;
            foreach (CelluleDeCarte cellule in carte.Lue.Cellules) foreach (VilleDeCarte ville in cellule.Villes) { moins = Math.Min(moins, ville.Population); plus = Math.Max(plus, ville.Population); }
            Transform noms = transform.Find(NOMS); int rang = 0;
            foreach (CelluleDeCarte cellule in carte.Lue.Cellules)
                foreach (VilleDeCarte ville in cellule.Villes)
                {
                    int taille = Taille(ville.Population, moins, plus); Vector3 pied = carte.PositionSurLaCarte(ville.Position, 0f).Value;
                    var objet = new GameObject("Figurine de " + ville.Nom, typeof(MeshFilter), typeof(MeshRenderer)); objet.transform.SetParent(racine, false); objet.transform.localPosition = pied;
                    objet.GetComponent<MeshFilter>().sharedMesh = Forme(taille);
                    var rendu = objet.GetComponent<MeshRenderer>(); rendu.sharedMaterial = Matiere(); rendu.shadowCastingMode = ShadowCastingMode.Off; rendu.receiveShadows = false;
                    // Les noms de la carte sont posés dans le même ordre que ses villes.
                    Transform nom = noms != null && rang < noms.childCount && noms.GetChild(rang).name == "Ville " + ville.Nom ? noms.GetChild(rang) : null; rang++;
                    posees.Add(new Posee { Figurine = objet.transform, Nom = nom, Pied = pied, Taille = taille, Habitants = ville.Population });
                }
            // Les plus peuplées d'abord ; à habitants égaux, dans l'ordre où la carte les sert.
            var ordre = new List<Posee>(posees); posees.Sort((a, b) => a.Habitants != b.Habitants ? b.Habitants.CompareTo(a.Habitants) : ordre.IndexOf(a).CompareTo(ordre.IndexOf(b)));
        }
        Mesh Forme(int taille) { if (formes[taille] == null) { formes[taille] = FormesDeCarte.Bourg(taille, SocleInterface.Couleur("papier"), SocleInterface.Couleur("encre"), null, Color.Lerp(SocleInterface.Couleur("papier"), SocleInterface.Couleur("or"), .35f)); crees.Add(formes[taille]); } return formes[taille]; }
        Material Matiere() { if (matiere == null) { matiere = FormesDeCarte.Matiere(SocleInterface.Couleur("cuivre")); matiere.name = RACINE; crees.Add(matiere); } return matiere; }
        static void Detruire(UnityEngine.Object o) { if (o == null) return; if (Application.isPlaying) Destroy(o); else DestroyImmediate(o); }
    }
}
