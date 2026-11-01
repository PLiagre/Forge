using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using Forge.Pont;
using UnityEngine;
using UnityEngine.UI;

namespace Forge.Interface
{
    public sealed class RepartitionHabitants
    {
        readonly Dictionary<long, long> populations = new Dictionary<long, long>();
        public long Minimum { get; }
        public long Maximum { get; }
        public string Legende { get; }
        public RepartitionHabitants(MondeLu monde)
        {
            if (monde == null || monde.Cellules.Count == 0 || monde.Cellules.Count != monde.CellCount)
                throw new ArgumentException("Population des territoires incomplète");
            foreach (var cellule in monde.Cellules)
            {
                if (cellule.Population < 0 || populations.ContainsKey(cellule.CellId))
                    throw new ArgumentException("Population négative ou territoire dupliqué");
                populations.Add(cellule.CellId, cellule.Population);
            }
            Minimum = populations.Values.Min(); Maximum = populations.Values.Max();
            string H(long n) => TexteDuMonde.Nombre(n) + (n < 2 ? " habitant" : " habitants");
            Legende = "Habitants : " + H(Minimum) + " (clair) → " + H(Maximum) + " (foncé) · échelle logarithmique · " + TexteDuMonde.Date(monde.Date);
        }
        public float Position(long cellId)
        {
            if (!populations.TryGetValue(cellId, out long nombre)) throw new ArgumentException("Population absente du territoire " + cellId);
            return Minimum == Maximum ? .5f : (float)(Math.Log(1d + nombre - Minimum) / Math.Log(1d + Maximum - Minimum));
        }
    }

    public sealed class CalquesCarte : MonoBehaviour
    {
        CarteDessinee carte;
        Func<MondeLu> monde;
        Func<CelluleDeCarte> selection;
        Dictionary<long, MeshRenderer> rendus;
        readonly Dictionary<long, (Material copie, Color maison)> teintes = new Dictionary<long, (Material, Color)>(); // couleur de la maison relevée une fois, jamais relue sur la copie teinte
        TextMesh[] noms;
        readonly List<Rect> etiquettes = new List<Rect>();
        Text legende;
        MondeLu precedent;
        long? territoirePrecedent;
        bool habitants, changement = true;
        public bool Habitants => habitants;
        public Text Legende => legende;
        public void Initialiser(CarteDessinee carte, Transform guide, Func<MondeLu> monde, Func<CelluleDeCarte> selection)
        {
            this.carte = carte; this.monde = monde; this.selection = selection;
            Bouton(guide, "Puissances", 650, false, "Colore la carte selon la maison qui tient chaque terre.");
            Bouton(guide, "Habitants", 928, true, "Colore la carte selon le nombre d'habitants de chaque terre.");
            legende = SocleInterface.Texte(guide, "Les calques attendent la carte…", 24, 128, 1190);
            legende.rectTransform.sizeDelta = new Vector2(1190, 44); legende.supportRichText = false;
        }
        void Bouton(Transform guide, string titre, float x, bool afficherHabitants, string phrase)
        {
            var b = SocleInterface.Commande(guide, titre, x, 24, () => { habitants = afficherHabitants; changement = true; }, phrase: phrase);
            b.GetComponent<RectTransform>().sizeDelta = new Vector2(260, 44);
            b.GetComponentInChildren<Text>().rectTransform.sizeDelta = new Vector2(260, 44);
        }
        void LateUpdate()
        {
            if (legende == null || carte.CellulesPosees == 0) return;
            EspacerLesNoms();
            var lu = monde(); long? retenu = selection()?.CellId;
            if (!changement && ReferenceEquals(lu, precedent) && retenu == territoirePrecedent) return;
            changement = false; precedent = lu; territoirePrecedent = retenu;
            try
            {
                if (rendus == null)
                {
                    var racine = carte.transform.Find("Cellules de la carte");
                    rendus = racine.GetComponentsInChildren<MeshRenderer>().ToDictionary(
                        r => long.Parse(r.name.Substring("Cellule ".Length), CultureInfo.InvariantCulture));
                    foreach (var r in rendus) { teintes.Add(r.Key, (new Material(r.Value.sharedMaterial), r.Value.sharedMaterial.color)); r.Value.sharedMaterial = teintes[r.Key].copie; }
                    carte.camera.backgroundColor = SocleInterface.Couleur("mer");
                    var police = SocleInterface.Police(titre: true);
                    noms = carte.GetComponentsInChildren<TextMesh>().OrderBy(n => n.text, StringComparer.Ordinal).ToArray();
                    foreach (var nom in noms)
                    {
                        nom.font = police; nom.fontSize = 16;
                        nom.GetComponent<MeshRenderer>().sharedMaterial = police.material;
                        nom.color = SocleInterface.Couleur("encre");
                    }
                }
                RepartitionHabitants repartition = habitants ? new RepartitionHabitants(lu) : null;
                if (habitants && rendus.Count != lu.Cellules.Count) throw new ArgumentException("Carte et populations ne couvrent pas les mêmes territoires");
                // Valider toutes les cellules avant de changer une seule couleur.
                if (habitants) foreach (long id in rendus.Keys) repartition.Position(id);
                foreach (var paire in rendus)
                {
                    paire.Value.SetPropertyBlock(null);
                    teintes[paire.Key].copie.color = paire.Key == retenu ? SocleInterface.Couleur("alerte")
                        : habitants ? Color.Lerp(SocleInterface.Couleur("papier"), SocleInterface.Couleur("accent"), .65f * repartition.Position(paire.Key))
                        : SocleInterface.Pigment(teintes[paire.Key].maison);
                }
                legende.text = LegendeDuCalque(repartition);
            }
            catch (Exception e)
            {
                if (rendus != null) foreach (var paire in rendus)
                {
                    paire.Value.SetPropertyBlock(null);
                    if (teintes.TryGetValue(paire.Key, out var t)) t.copie.color = paire.Key == retenu ? SocleInterface.Couleur("alerte") : SocleInterface.Pigment(t.maison);
                }
                legende.text = Indisponible(e.Message);
            }
        }
        void OnDestroy() { foreach (var t in teintes.Values) if (Application.isPlaying) Destroy(t.copie); else DestroyImmediate(t.copie); teintes.Clear(); }

        // Lot #943 : sans année. Les couleurs des puissances sont relevées au dessin de la carte, jamais relues : les dater
        // dirait qu'elles sont celles du jour servi. La légende des habitants garde sa date, celle du monde lu.
        public static string LegendeDuCalque(RepartitionHabitants repartition) =>
            (repartition == null ? "Puissances de la carte · Relief non transmis" : repartition.Legende) + " · Rouge : territoire conservé";
        public static string Indisponible(string raison) => "Calque indisponible : " + TexteDuMonde.Absence(raison) + ". Couleurs des puissances conservées.";
        void EspacerLesNoms()
        {
            if (noms == null) return;
            etiquettes.Clear();
            foreach (var nom in noms)
            {
                var rendu = nom.GetComponent<MeshRenderer>();
                var bounds = rendu.bounds;
                var a = carte.camera.WorldToScreenPoint(bounds.min);
                var b = carte.camera.WorldToScreenPoint(bounds.max);
                var rect = Rect.MinMaxRect(Mathf.Min(a.x, b.x) - 3, Mathf.Min(a.y, b.y) - 2,
                    Mathf.Max(a.x, b.x) + 3, Mathf.Max(a.y, b.y) + 2);
                bool visible = carte.camera.pixelRect.Contains(rect.center) && !etiquettes.Any(r => r.Overlaps(rect));
                rendu.enabled = visible;
                if (visible) etiquettes.Add(rect);
            }
        }
    }
}
