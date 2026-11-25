using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Forge.Interface;
using Forge.Pont;
using UnityEngine;

namespace ForgeLocal3D.Captures
{
    // Le garde d'un défaut de texte : un nom inventé (tiré des listes de noms plausibles du moteur, `jeu/data/noms-1400.json`) écrit à la place d'un pays.
    // Les noms de lieux et de maisons de toutes les aires sont lus une fois ; un texte est fautif quand il vaut un de ces noms, ou quand il contient un nom de
    // maison entier (un nom de lieu seul ne se cherche pas en sous-chaîne : des noms courts recouvriraient de vrais noms). `TextesDePays` est le seul endroit
    // qui rassemble les textes qui écrivent un pays ; `Verifier` se prouve à chaque appel sur un nom planté, et refuse un échantillon vide.
    static class TextesDeCapture
    {
        static HashSet<string> lieux, maisons;

        internal static HashSet<string> Lieux { get { Lire(); return lieux; } }
        internal static HashSet<string> Maisons { get { Lire(); return maisons; } }

        // `jeu/data/noms-1400.json`, depuis le projet Unity.
        static string Fichier => Path.GetFullPath(Path.Combine(Application.dataPath, "..", "..", "..", "jeu", "data", "noms-1400.json"));

        static void Lire()
        {
            if (lieux != null) return;
            string chemin = Fichier;
            if (!File.Exists(chemin)) throw Faux("pas de " + chemin);
            LecteurJson.LireObjet(File.ReadAllText(chemin)).TryGetValue("aires", out object brut);
            var aires = brut as Dictionary<string, object> ?? throw Faux("« aires » manque ou n'est pas un objet dans " + chemin);
            var l = new HashSet<string>(StringComparer.Ordinal); var m = new HashSet<string>(StringComparer.Ordinal);
            foreach (var aire in aires.Values.OfType<Dictionary<string, object>>())
            {
                if (aire.TryGetValue("lieux", out object nl) && nl is List<object> ls) foreach (string n in ls.OfType<string>()) l.Add(n);
                if (aire.TryGetValue("maisons", out object nm) && nm is List<object> ms) foreach (string n in ms.OfType<string>()) m.Add(n);
            }
            if (l.Count == 0) throw Faux("aucun nom de lieu lu dans " + chemin);
            if (m.Count == 0) throw Faux("aucun nom de maison lu dans " + chemin);
            maisons = m; lieux = l;
        }

        // Les textes (comparés après `Trim`) qui valent un nom de lieu ou de maison, ou qui contiennent un nom de maison entier ; sans doublon, en ordre ordinal.
        internal static List<string> Fautifs(IEnumerable<string> textes)
        {
            var noms = Maisons; var seuls = Lieux;
            return textes.Where(t => t != null).Select(t => t.Trim()).Where(t => seuls.Contains(t) || noms.Contains(t) || noms.Any(n => ContientEntier(t, n))).Distinct(StringComparer.Ordinal).OrderBy(t => t, StringComparer.Ordinal).ToList();
        }

        // `nom` apparaît dans `texte`, borné au début et à la fin par le bord du texte ou par un caractère qui n'est ni lettre ni chiffre.
        static bool ContientEntier(string texte, string nom)
        {
            if (nom.Length == 0) return false;
            for (int i = texte.IndexOf(nom, StringComparison.Ordinal); i >= 0; i = texte.IndexOf(nom, i + 1, StringComparison.Ordinal))
            {
                int fin = i + nom.Length;
                if ((i == 0 || !char.IsLetterOrDigit(texte[i - 1])) && (fin == texte.Length || !char.IsLetterOrDigit(texte[fin]))) return true;
            }
            return false;
        }

        // Les textes qui écrivent un pays à l'écran : le nom de chaque pays sur la carte et sa ligne de vassalité (pas sa maison, une dynastie qui peut porter un nom de maison),
        // puis, l'accueil ouvert, le nom de sa fiche et le nom de pays qui ouvre la fiche (« Bohême : … » ; la ligne « Maison … » est une dynastie).
        // Le cabinet n'écrit aucun autre nom de pays : sa barre et « Votre maison » disent la maison du joueur, une dynastie.
        internal static List<string> TextesDePays(CarteDeLaGuerre guerre, CabinetDeCarte cabinet)
        {
            var textes = new List<string>();
            foreach (var n in guerre.NomsDesPays)
            {
                textes.Add(n.Texte);
                if (n.Vassalite != null) textes.Add(n.Vassalite.Texte);
            }
            if (cabinet.Accueil.Ouvert)
            {
                if (!string.IsNullOrEmpty(cabinet.Accueil.TexteDuNom)) textes.Add(cabinet.Accueil.TexteDuNom);
                string fiche = cabinet.Accueil.TexteDeLaFiche ?? "";
                string premiere = fiche.Split('\n')[0]; int deuxPoints = premiere.IndexOf(':');
                if (deuxPoints >= 0) textes.Add(premiere.Substring(0, deuxPoints));
            }
            return textes;
        }

        // `ou` dit l'écran ou le pas. Le contrôle se prouve d'abord sur un nom de maison planté dans un texte ; un échantillon vide échoue ; les fautifs sont tous nommés.
        internal static void Verifier(IEnumerable<string> textes, string ou)
        {
            string plante = Maisons.OrderBy(n => n, StringComparer.Ordinal).First(), entoure = "Royaume " + plante;
            if (!Fautifs(new[] { entoure }).Contains(entoure)) throw Faux("le contrôle ne prouve plus rien : « " + plante + " » n'est pas reconnu");
            var juges = textes.Where(t => !string.IsNullOrWhiteSpace(t)).ToList();
            if (juges.Count == 0) throw Faux(ou + " : aucun texte de pays à juger");
            var fautifs = Fautifs(juges);
            if (fautifs.Count > 0) throw Faux(ou + " : des noms inventés sont écrits à la place d'un pays : " + string.Join(", ", fautifs));
        }

        internal static void Verifier(CarteDeLaGuerre guerre, CabinetDeCarte cabinet, string ou) => Verifier(TextesDePays(guerre, cabinet), ou);

        static InvalidOperationException Faux(string raison) => new InvalidOperationException("noms inventés : " + raison);
    }
}
