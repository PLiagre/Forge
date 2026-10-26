using System;
using System.Globalization;
using System.Threading.Tasks;
using Forge.Pont;
using UnityEngine;

namespace Forge.Interface
{
    public sealed class OrdreConfirme
    {
        public string Brouillon { get; private set; }
        public string Resume { get; private set; }
        public RecuIntention Recu { get; private set; }
        public bool EnCours { get; private set; }
        readonly Func<string, Task<RecuIntention>> envoyer;
        public OrdreConfirme(Func<string, Task<RecuIntention>> envoyer)
        {
            this.envoyer = envoyer ?? throw new ArgumentNullException(nameof(envoyer));
        }
        public bool Preparer(string json, string resume)
        {
            if (EnCours || Recu != null) return false;
            LecteurJson.LireObjet(json);
            if (string.IsNullOrWhiteSpace(resume)) throw new ArgumentException("Résumé de confirmation absent");
            Brouillon = json; Resume = resume;
            return true;
        }
        public void Annuler()
        {
            if (EnCours || Recu != null) return;
            Brouillon = null; Resume = null;
        }
        // Geste explicite du joueur après lecture du reçu, jamais appelé par une minuterie.
        public bool Recommencer()
        {
            if (EnCours) return false;
            Recu = null; Brouillon = null; Resume = null;
            return true;
        }
        public async Task Confirmer()
        {
            if (EnCours || Recu != null || Brouillon == null) return;
            EnCours = true;
            try { Recu = await envoyer(Brouillon) ?? RecuIntention.Absente("Réponse absente"); }
            catch (Exception erreur) { Recu = RecuIntention.Absente(erreur.GetBaseException().Message); }
            finally { EnCours = false; }
        }
        public static OrdreConfirme Local(int port) => new OrdreConfirme(json => Task.Run(() =>
        {
            using (var client = new ClientIntention(port, TimeSpan.FromSeconds(5))) return client.Deposer(json);
        }));
    }
    public static class OrdresMaison
    {
        [Serializable] sealed class FixerPart { public string type = "fixer_part", maison; public double part; }
        [Serializable] sealed class OuvrirGrenier { public string type = "ouvrir_grenier", maison; public double kg; }
        static string Maison(string maison) => !string.IsNullOrWhiteSpace(maison) ? maison : throw new ArgumentException("Maison non confirmée par le monde");
        static double Quantite(string texte)
        {
            if (!double.TryParse((texte ?? "").Trim().Replace(',', '.'), NumberStyles.AllowDecimalPoint | NumberStyles.AllowLeadingSign,
                CultureInfo.InvariantCulture, out double nombre) || double.IsNaN(nombre) || double.IsInfinity(nombre) || nombre < 0)
                throw new ArgumentException("Saisissez une quantité positive ou nulle, avec une virgule ou un point");
            return nombre;
        }
        public static string Part(string maison, string pourcentage)
        {
            double pourcent = Quantite(pourcentage);
            if (pourcent > 100) throw new ArgumentException("Un pourcentage est compris entre 0 et 100");
            return JsonUtility.ToJson(new FixerPart { maison = Maison(maison), part = pourcent / 100 });
        }
        public static string Grenier(string maison, string kg)
        {
            double quantite = Quantite(kg);
            if (quantite <= 0) throw new ArgumentException("Indiquez une quantité supérieure à zéro kg");
            return JsonUtility.ToJson(new OuvrirGrenier { maison = Maison(maison), kg = quantite });
        }
    }
}
