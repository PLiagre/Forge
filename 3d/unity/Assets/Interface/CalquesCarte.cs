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
        Text legende;
        MondeLu precedent;
        long? territoirePrecedent;
        bool habitants, changement = true;
        public bool Habitants => habitants;
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
                }
                RepartitionHabitants repartition = habitants ? new RepartitionHabitants(lu) : null;
                if (habitants && rendus.Count != lu.Cellules.Count) throw new ArgumentException("Carte et populations ne couvrent pas les mêmes territoires");
                // Valider toutes les cellules avant de changer une seule couleur.
                if (habitants) foreach (long id in rendus.Keys) repartition.Position(id);
                foreach (var paire in rendus)
                {
                    paire.Value.SetPropertyBlock(null);
                    if (!habitants && paire.Key != retenu) continue;
                    var bloc = new MaterialPropertyBlock();
                    bloc.SetColor("_BaseColor", (paire.Key == retenu ? SocleInterface.Couleur("alerte")
                        : Color.Lerp(SocleInterface.Couleur("papier"), SocleInterface.Couleur("accent"), .65f * repartition.Position(paire.Key))).linear);
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
                    if (paire.Key != retenu) continue;
                    var bloc = new MaterialPropertyBlock(); bloc.SetColor("_BaseColor", SocleInterface.Couleur("alerte").linear);
                    paire.Value.SetPropertyBlock(bloc);
                }
                legende.text = "Calque indisponible : " + e.Message + ". Couleurs des puissances conservées.";
            }
        }
    }
}
