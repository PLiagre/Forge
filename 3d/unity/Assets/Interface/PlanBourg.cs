using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;

namespace Forge.Interface
{
    public sealed class PlanBourg
    {
        public sealed class Trace { public Vector2[] Points; public float Largeur; public string Nature; public bool Fermee; }
        public long Tick { get; }
        public IReadOnlyList<Trace> Traces { get; }
        public Vector2 Minimum { get; }
        public Vector2 Maximum { get; }
        public PlanBourg(DocumentDuMonde document, long cellule)
        {
            if (DocumentDuMonde.Entier(document.Champs, "cell_id") != cellule)
                throw new ArgumentException("Le plan reçu concerne un autre territoire");
            Tick = document.Tick;
            var fond = DocumentDuMonde.Objet(document.Champs, "base");
            if (DocumentDuMonde.Entier(fond, "cell_id") != cellule) throw new ArgumentException("Fond du plan incohérent");
            var traces = new List<Trace> { Lire(fond, "place", "place", true) };
            Ajouter(traces, fond, "maisons", "emprise", "maison", true, false);
            Ajouter(traces, fond, "rues", "points", "rue", false, false);
            Ajouter(traces, document.Champs, "rues", "points", "rue", false, true);
            Ajouter(traces, document.Champs, "parcelles", "contour", "parcelle", true, true);
            Ajouter(traces, document.Champs, "batiments", "emprise", "maison", true, true);
            Traces = traces.AsReadOnly();
            var points = traces.SelectMany(t => t.Points).ToArray();
            Minimum = new Vector2(points.Min(p => p.x), points.Min(p => p.y));
            Maximum = new Vector2(points.Max(p => p.x), points.Max(p => p.y));
            if (Maximum.x <= Minimum.x || Maximum.y <= Minimum.y) throw new ArgumentException("Plan sans étendue");
        }
        static void Ajouter(List<Trace> traces, Dictionary<string, object> source, string liste, string points, string nature, bool ferme, bool chantier)
        {
            var identifiants = new HashSet<long>();
            foreach (var brut in DocumentDuMonde.Tableau(source, liste))
            {
                var objet = brut as Dictionary<string, object> ?? throw new ArgumentException("Forme absente : " + liste);
                string aspect = nature;
                if (chantier)
                {
                    if (!identifiants.Add(DocumentDuMonde.Entier(objet, "identifiant"))) throw new ArgumentException("Forme dupliquée : " + liste);
                    if (!(DocumentDuMonde.Valeur(objet, "en_chantier") is bool enCours)) throw new ArgumentException("État du chantier absent");
                    if (enCours) aspect = "chantier";
                }
                traces.Add(Lire(objet, points, aspect, ferme));
            }
        }
        static Trace Lire(Dictionary<string, object> objet, string cle, string nature, bool ferme)
        {
            var points = DocumentDuMonde.Tableau(objet, cle);
            if (points.Count < (ferme ? 3 : 2)) throw new ArgumentException("Forme incomplète : " + cle);
            var trace = new Trace { Points = new Vector2[points.Count], Nature = nature, Fermee = ferme, Largeur = 1 };
            for (int i = 0; i < points.Count; i++)
            {
                var paire = points[i] as List<object>;
                if (paire == null || paire.Count != 2) throw new ArgumentException("Deux coordonnées attendues");
                trace.Points[i] = new Vector2(Coordonnée(paire[0]), Coordonnée(paire[1]));
            }
            if (!ferme)
            {
                trace.Largeur = Coordonnée(DocumentDuMonde.Nombre(objet, "largeur_m"));
                if (trace.Largeur <= 0) throw new ArgumentException("Largeur de rue invalide");
            }
            return trace;
        }
        static float Coordonnée(object valeur)
        {
            if (!(valeur is double n) || double.IsNaN(n) || double.IsInfinity(n) || Math.Abs(n) > 10000000)
                throw new ArgumentException("Coordonnée locale non représentable");
            return (float)n;
        }
    }
}
