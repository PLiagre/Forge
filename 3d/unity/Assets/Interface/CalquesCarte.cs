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
            Legende = "Habitants : " + Minimum + " (clair) → " + Maximum + " (foncé) · échelle logarithmique · tick " + monde.Tick;
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
        TextMesh[] noms;
        readonly List<Rect> etiquettes = new List<Rect>();
        Text legende;
        MondeLu precedent;
        long? territoirePrecedent;
        bool habitants, changement = true;
        public bool Habitants => habitants;
        // Pigments d'atlas : la teinte politique reste celle reçue, seule sa présentation change.
        public static Color Pigment(Color couleur)
        {
            Color.RGBToHSV(couleur, out float teinte, out float saturation, out float valeur);
            return Color.Lerp(Color.HSVToRGB(teinte, saturation * .38f, .53f + valeur * .08f),
                SocleInterface.Couleur("papier"), .16f);
        }
        public void Initialiser(CarteDessinee carte, Transform guide, Func<MondeLu> monde, Func<CelluleDeCarte> selection)
        {
            this.carte = carte; this.monde = monde; this.selection = selection;
            Bouton(guide, "Puissances", 650, false); Bouton(guide, "Habitants", 928, true);
            legende = SocleInterface.Texte(guide, "Les calques attendent la carte…", 24, 128, 1190);
            legende.rectTransform.sizeDelta = new Vector2(1190, 44); legende.supportRichText = false;
        }
        void Bouton(Transform guide, string titre, float x, bool afficherHabitants)
        {
            var b = SocleInterface.Commande(guide, titre, x, 24, () => { habitants = afficherHabitants; changement = true; });
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
                    carte.camera.backgroundColor = new Color(.22f, .29f, .30f);
                    var police = Resources.Load<Font>("Forge/Polices/NotoSerif-Regular");
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
                    var bloc = new MaterialPropertyBlock();
                    bloc.SetColor("_BaseColor", (paire.Key == retenu ? SocleInterface.Couleur("alerte")
                        : habitants ? Color.Lerp(SocleInterface.Couleur("papier"), SocleInterface.Couleur("accent"), .65f * repartition.Position(paire.Key))
                        : Pigment(paire.Value.sharedMaterial.color)).linear);
                    paire.Value.SetPropertyBlock(bloc);
                }
                legende.text = (habitants ? repartition.Legende : "Puissances de la carte de 1400 · Relief non transmis")
                    + " · Rouge : territoire conservé";
            }
            catch (Exception e)
            {
                if (rendus != null) foreach (var paire in rendus)
                {
                    paire.Value.SetPropertyBlock(null);
                    var bloc = new MaterialPropertyBlock();
                    bloc.SetColor("_BaseColor", (paire.Key == retenu ? SocleInterface.Couleur("alerte")
                        : Pigment(paire.Value.sharedMaterial.color)).linear);
                    paire.Value.SetPropertyBlock(bloc);
                }
                legende.text = "Calque indisponible : " + e.Message + ". Couleurs des puissances conservées.";
            }
        }

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
