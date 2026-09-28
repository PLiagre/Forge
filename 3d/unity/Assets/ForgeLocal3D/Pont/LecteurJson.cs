using System;
using System.Collections.Generic;
using System.Globalization;

namespace Forge.Pont
{
    // Un texte JSON refusé : la position (index du caractère) dit où la lecture a buté.
    public sealed class ErreurJson : FormatException
    {
        public int Position { get; }

        public ErreurJson(int position, string attendu)
            : base("JSON invalide à la position " + position + " : " + attendu + " attendu")
        {
            Position = position;
        }
    }

    // Lit le JSON du service de `sim/` sans connaître aucune clé : objets en
    // dictionnaires (ordre du texte), tableaux en listes, nombres en double.
    // Un texte cassé lève ErreurJson ; rien n'est deviné, rien n'est rendu vide.
    public static class LecteurJson
    {
        public static object Lire(string texte) => Racine(texte, false);

        public static Dictionary<string, object> LireObjet(string texte) =>
            (Dictionary<string, object>)Racine(texte, true);

        private static object Racine(string texte, bool exigerObjet)
        {
            if (texte == null) throw new ArgumentNullException(nameof(texte));
            var lecteur = new Curseur(texte);
            lecteur.Blancs();
            if (exigerObjet && (lecteur.I >= texte.Length || texte[lecteur.I] != '{'))
                throw new ErreurJson(lecteur.I, "un objet '{' à la racine");
            object valeur = lecteur.Valeur();
            lecteur.Blancs();
            if (lecteur.I < texte.Length) throw new ErreurJson(lecteur.I, "la fin du texte");
            return valeur;
        }

        private sealed class Curseur
        {
            private readonly string t;
            public int I;

            public Curseur(string texte) { t = texte; }

            public void Blancs()
            {
                while (I < t.Length && (t[I] == ' ' || t[I] == '\t' || t[I] == '\n' || t[I] == '\r')) I++;
            }

            private char Courant(string attendu)
            {
                if (I >= t.Length) throw new ErreurJson(I, attendu);
                return t[I];
            }

            private void Exiger(char c)
            {
                if (Courant("'" + c + "'") != c) throw new ErreurJson(I, "'" + c + "'");
                I++;
            }

            public object Valeur()
            {
                char c = Courant("une valeur");
                if (c == '{') return Objet();
                if (c == '[') return Tableau();
                if (c == '"') return Chaine();
                if (c == '-' || (c >= '0' && c <= '9')) return Nombre();
                if (Mot("true")) return true;
                if (Mot("false")) return false;
                if (Mot("null")) return null;
                throw new ErreurJson(I, "une valeur");
            }

            private bool Mot(string mot)
            {
                if (I + mot.Length > t.Length || string.CompareOrdinal(t, I, mot, 0, mot.Length) != 0) return false;
                I += mot.Length;
                return true;
            }

            private Dictionary<string, object> Objet()
            {
                var objet = new Dictionary<string, object>();
                Exiger('{');
                Blancs();
                if (Courant("une clé ou '}'") == '}') { I++; return objet; }
                while (true)
                {
                    Blancs();
                    int debut = I;
                    if (Courant("une clé") != '"') throw new ErreurJson(I, "une clé");
                    string cle = Chaine();
                    if (objet.ContainsKey(cle)) throw new ErreurJson(debut, "une clé non répétée (\"" + cle + "\" déjà lue)");
                    Blancs();
                    Exiger(':');
                    Blancs();
                    objet.Add(cle, Valeur());
                    Blancs();
                    if (Courant("',' ou '}'") == '}') { I++; return objet; }
                    Exiger(',');
                }
            }

            private List<object> Tableau()
            {
                var liste = new List<object>();
                Exiger('[');
                Blancs();
                if (Courant("une valeur ou ']'") == ']') { I++; return liste; }
                while (true)
                {
                    Blancs();
                    liste.Add(Valeur());
                    Blancs();
                    if (Courant("',' ou ']'") == ']') { I++; return liste; }
                    Exiger(',');
                }
            }

            private string Chaine()
            {
                Exiger('"');
                var sortie = new System.Text.StringBuilder();
                while (true)
                {
                    char c = Courant("'\"' fermant");
                    if (c == '"') { I++; return sortie.ToString(); }
                    if (c < ' ') throw new ErreurJson(I, "un caractère de chaîne (contrôle non échappé)");
                    if (c != '\\') { sortie.Append(c); I++; continue; }
                    I++;
                    char e = Courant("un échappement");
                    switch (e)
                    {
                        case '"': sortie.Append('"'); break;
                        case '\\': sortie.Append('\\'); break;
                        case '/': sortie.Append('/'); break;
                        case 'b': sortie.Append('\b'); break;
                        case 'f': sortie.Append('\f'); break;
                        case 'n': sortie.Append('\n'); break;
                        case 'r': sortie.Append('\r'); break;
                        case 't': sortie.Append('\t'); break;
                        case 'u':
                            if (I + 5 > t.Length) throw new ErreurJson(t.Length, "quatre chiffres hexadécimaux");
                            if (!int.TryParse(t.Substring(I + 1, 4), NumberStyles.AllowHexSpecifier, CultureInfo.InvariantCulture, out int code))
                                throw new ErreurJson(I + 1, "quatre chiffres hexadécimaux");
                            sortie.Append((char)code);
                            I += 4;
                            break;
                        default: throw new ErreurJson(I, "un échappement valide");
                    }
                    I++;
                }
            }

            private double Nombre()
            {
                int debut = I;
                if (t[I] == '-') I++;
                if (Courant("un chiffre") == '0') I++;
                else Chiffres();
                if (I < t.Length && t[I] == '.') { I++; Chiffres(); }
                if (I < t.Length && (t[I] == 'e' || t[I] == 'E'))
                {
                    I++;
                    if (I < t.Length && (t[I] == '+' || t[I] == '-')) I++;
                    Chiffres();
                }
                if (!double.TryParse(t.Substring(debut, I - debut), NumberStyles.Float, CultureInfo.InvariantCulture, out double valeur)
                    || double.IsInfinity(valeur))
                    throw new ErreurJson(debut, "un nombre représentable en double");
                return valeur;
            }

            private void Chiffres()
            {
                char c = Courant("un chiffre");
                if (c < '0' || c > '9') throw new ErreurJson(I, "un chiffre");
                while (I < t.Length && t[I] >= '0' && t[I] <= '9') I++;
            }
        }
    }
}
