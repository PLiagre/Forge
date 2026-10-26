using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using UnityEngine;

namespace Forge.Interface
{
    public static class OrdreRue
    {
        [Serializable] sealed class Parametres { public string type = "tracer_route", maison; public long cell; public double largeur_m; public int foyers; }
        public static bool Permis(DocumentDuMonde lieu, long cellule, string maison)
        {
            if (lieu == null || string.IsNullOrEmpty(maison) || DocumentDuMonde.Entier(lieu.Champs, "cell_id") != cellule) return false;
            var bourgs = DocumentDuMonde.Tableau(lieu.Champs, "lieux").Cast<Dictionary<string, object>>()
                .Where(l => DocumentDuMonde.Entier(l, "rang") == 0).ToArray();
            return bourgs.Length == 1 && DocumentDuMonde.Valeur(bourgs[0], "maitre") as string == maison;
        }
        public static string Creer(string maison, long cellule, Vector2[] points, string largeur, string foyers)
        {
            if (string.IsNullOrWhiteSpace(maison) || cellule < 0) throw new ArgumentException("Maison ou territoire absent");
            if (points == null || points.Length < 2 || points.Any(p => float.IsNaN(p.x) || float.IsNaN(p.y) || float.IsInfinity(p.x) || float.IsInfinity(p.y)))
                throw new ArgumentException("Placez au moins deux points valides");
            if (!double.TryParse((largeur ?? "").Replace(',', '.'), NumberStyles.AllowDecimalPoint, CultureInfo.InvariantCulture, out double metres) || metres <= 0 || double.IsNaN(metres) || double.IsInfinity(metres))
                throw new ArgumentException("Indiquez une largeur positive en mètres");
            if (!int.TryParse(foyers, NumberStyles.None, CultureInfo.InvariantCulture, out int nombre) || nombre < 1)
                throw new ArgumentException("Indiquez au moins un foyer");
            string json = JsonUtility.ToJson(new Parametres { maison = maison, cell = cellule, largeur_m = metres, foyers = nombre });
            string trace = string.Join(",", points.Select(p => "[" + p.x.ToString("R", CultureInfo.InvariantCulture) + "," + p.y.ToString("R", CultureInfo.InvariantCulture) + "]"));
            return json.Substring(0, json.Length - 1) + ",\"points\":[" + trace + "]}";
        }
    }
}
