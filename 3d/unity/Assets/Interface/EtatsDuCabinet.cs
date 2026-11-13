using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using UnityEngine.UI;
using Usage = Forge.Interface.SocleInterface.Usage;

namespace Forge.Interface
{
    public enum EtatDuCabinet { Repos, Survol, Focus, Selection, Inactif, Attente, Recu, Refus, Alerte }
    public enum FormeDuTrait { Aucun, Plein, Double, Pointille }

    // Lot #849 : ce qu'un état déclare, une seule fois pour tous les écrans. `Trait` vaut null quand la forme est `Aucun`.
    public readonly struct Declaration
    {
        public readonly string Nom, Matiere, Texte, Trait, Signe, Mot;
        public readonly FormeDuTrait Forme;
        public readonly int Epaisseur;
        public Declaration(string nom, string matiere, string texte, string trait, FormeDuTrait forme, int epaisseur, string signe, string mot)
        { Nom = nom; Matiere = matiere; Texte = texte; Trait = trait; Forme = forme; Epaisseur = epaisseur; Signe = signe; Mot = mot; }
    }

    public static class EtatsDuCabinet
    {
        static readonly Declaration[] table =
        {
            new Declaration("repos", "bois-brule", "papier", "metal", FormeDuTrait.Plein, 1, null, null),
            new Declaration("survol", "bois-brule", "papier", "cuivre", FormeDuTrait.Plein, 2, null, null),
            new Declaration("focus clavier", "bois-brule", "papier", "or-vieilli", FormeDuTrait.Double, 2, null, null),
            new Declaration("sélection", "bois-brule", "papier", "or-vieilli", FormeDuTrait.Plein, 4, null, "Choisi"),
            new Declaration("inactif", "metal", "attenue", null, FormeDuTrait.Aucun, 0, null, "Indisponible"),
            new Declaration("attente", "bois-brule", "papier", "papier", FormeDuTrait.Pointille, 1, "…", "En attente du monde"),
            new Declaration("reçu", "pierre", "vert-de-gris", "vert-de-gris", FormeDuTrait.Plein, 2, null, "Ordre reçu"),
            new Declaration("refus", "papier", "sang", "sang", FormeDuTrait.Plein, 2, "×", "Demande refusée"),
            new Declaration("alerte", "sang", "papier", null, FormeDuTrait.Aucun, 0, "!", "Alerte")
        };
        public static IReadOnlyList<Declaration> Table => table;
        public static Declaration De(EtatDuCabinet etat) => (int)etat >= 0 && (int)etat < table.Length ? table[(int)etat] : throw new ArgumentOutOfRangeException(nameof(etat));

        // Le texte de chaque état sur sa matière, et son trait sur sa matière ; le filet du repos est décoratif, il ne porte aucun état.
        public static IEnumerable<(string, string, Usage)> PairesDesEtats()
        {
            for (int i = 0; i < table.Length; i++)
            {
                yield return (table[i].Texte, table[i].Matiere, Usage.Texte);
                if (table[i].Forme != FormeDuTrait.Aucun && i != (int)EtatDuCabinet.Repos) yield return (table[i].Trait, table[i].Matiere, Usage.Trait);
            }
        }

        // null si chaque paire d'états diffère par la forme, l'épaisseur, le signe ou le mot : les jetons ne comptent pas.
        public static string Confondus(IEnumerable<Declaration> declarations)
        {
            var t = declarations.ToArray();
            for (int i = 0; i < t.Length; i++)
                for (int j = i + 1; j < t.Length; j++)
                    if (t[i].Forme == t[j].Forme && t[i].Epaisseur == t[j].Epaisseur && t[i].Signe == t[j].Signe && t[i].Mot == t[j].Mot)
                        return t[i].Nom + " et " + t[j].Nom + " ne diffèrent que par leur teinte";
            return null;
        }

        static void Barre(RectTransform plaque, string nom, float x, float y, float largeur, float hauteur, Color couleur) =>
            SocleInterface.Aplat(SocleInterface.Cadre(plaque, nom, x, y, largeur, hauteur), couleur);

        // Quatre barres d'épaisseur e, à `dedans` px du bord : le haut et le bas, puis les deux côtés entre elles.
        static void Cadre(RectTransform plaque, float dedans, float e, float largeur, float hauteur, Color couleur)
        {
            float cote = hauteur - 2 * (dedans + e);
            Barre(plaque, "Trait", dedans, dedans, largeur - 2 * dedans, e, couleur);
            Barre(plaque, "Trait", dedans, hauteur - dedans - e, largeur - 2 * dedans, e, couleur);
            Barre(plaque, "Trait", dedans, dedans + e, e, cote, couleur);
            Barre(plaque, "Trait", largeur - dedans - e, dedans + e, e, cote, couleur);
        }

        // Des tirets de 10 px, séparés de 6 px, sur les quatre côtés ; aucun n'est plus mince que le trait.
        static void Tirets(RectTransform plaque, float e, float largeur, float hauteur, Color couleur)
        {
            for (float x = 0; largeur - x >= e; x += 16)
            {
                float l = Mathf.Min(10, largeur - x);
                Barre(plaque, "Tiret", x, 0, l, e, couleur); Barre(plaque, "Tiret", x, hauteur - e, l, e, couleur);
            }
            for (float y = e; hauteur - e - y >= e; y += 16)
            {
                float h = Mathf.Min(10, hauteur - e - y);
                Barre(plaque, "Tiret", 0, y, e, h, couleur); Barre(plaque, "Tiret", largeur - e, y, e, h, couleur);
            }
        }

        // Une plaque « État <nom> » : la matière, le trait fait de barres, puis le signe, le mot et le libellé qui reviennent à la ligne.
        public static RectTransform Poser(Transform parent, EtatDuCabinet etat, string libelle, float x, float y, float largeur, float hauteur)
        {
            var d = De(etat);
            if (string.IsNullOrWhiteSpace(libelle)) throw new ArgumentException("libellé vide refusé pour l'état " + d.Nom, nameof(libelle));
            var plaque = SocleInterface.Cadre(parent, "État " + d.Nom, x, y, largeur, hauteur);
            var fond = plaque.gameObject.AddComponent<Image>(); fond.raycastTarget = false;
            Sprite matiere = MatieresCabinet.Matiere(d.Matiere);
            if (matiere != null) { fond.sprite = matiere; fond.type = Image.Type.Tiled; } else fond.color = SocleInterface.Couleur(d.Matiere);
            if (d.Forme != FormeDuTrait.Aucun)
            {
                Color trait = SocleInterface.Teinte(d.Trait);
                if (d.Forme == FormeDuTrait.Pointille) Tirets(plaque, d.Epaisseur, largeur, hauteur, trait);
                else
                {
                    Cadre(plaque, 0, d.Epaisseur, largeur, hauteur, trait);
                    if (d.Forme == FormeDuTrait.Double) Cadre(plaque, d.Epaisseur + 4, d.Epaisseur, largeur, hauteur, trait);
                }
            }
            const float marge = 12;
            var dit = SocleInterface.Texte(plaque, string.Join(" ", new[] { d.Signe, d.Mot, libelle }.Where(s => s != null)), marge, marge, largeur - 2 * marge);
            dit.rectTransform.sizeDelta = new Vector2(largeur - 2 * marge, hauteur - 2 * marge); dit.color = SocleInterface.Teinte(d.Texte);
            return plaque;
        }
    }
}
