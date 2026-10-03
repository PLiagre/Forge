using System;
using System.Collections.Generic;
using System.Globalization;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Text;
using System.Threading;

namespace Forge.Pont
{
    // Le reçu d'une intention tel que `sim/` le rend : acceptée au tick qu'il nomme,
    // refusée avec sa raison, ou absente avec sa cause. Trois états, jamais mêlés.
    public sealed class RecuIntention
    {
        public bool Presente => Absence == null;
        public bool Acceptee => AppliqueeAuTick != null;
        public long? AppliqueeAuTick { get; }
        public int? Statut { get; }
        public string Erreur { get; }
        public string Absence { get; }

        private RecuIntention(long? tick, int? statut, string erreur, string absence)
        {
            AppliqueeAuTick = tick; Statut = statut; Erreur = erreur; Absence = absence;
        }

        // `AccepteeAu` et non `Acceptee` : C# refuse une méthode du nom d'une propriété.
        public static RecuIntention AccepteeAu(long tick) =>
            tick >= 0 ? new RecuIntention(tick, 200, null, null) : throw new ArgumentException("un tick ≥ 0 attendu", nameof(tick));

        public static RecuIntention Refusee(int statut, string erreur) =>
            (statut == 400 || statut == 409) && !string.IsNullOrEmpty(erreur) ? new RecuIntention(null, statut, erreur, null)
            : throw new ArgumentException("un refus porte le statut 400 ou 409 et nomme sa raison", nameof(statut));

        public static RecuIntention Absente(string cause) =>
            !string.IsNullOrEmpty(cause) ? new RecuIntention(null, null, null, cause) : throw new ArgumentException("une absence nomme sa cause", nameof(cause));
    }

    // Dépose une intention au service local (`POST /intention` sur 127.0.0.1) et relit son reçu.
    // Ne juge pas l'intention, ne recalcule rien ; ne lève jamais pour une cause du service.
    public sealed class ClientIntention : IDisposable
    {
        private const string Hote = "127.0.0.1";
        private readonly int port;
        private readonly TimeSpan delai;
        private readonly HttpClient http;

        public ClientIntention(int port, TimeSpan delai)
        {
            if (port < 1 || port > 65535) throw new ArgumentOutOfRangeException(nameof(port), port, "port hors de 1..65535");
            if (delai <= TimeSpan.Zero && delai != Timeout.InfiniteTimeSpan)
                throw new ArgumentOutOfRangeException(nameof(delai), delai, "un délai positif attendu");
            this.port = port;
            this.delai = delai;
            // Aucune redirection suivie : un 3xx est un statut inattendu. Le délai est tenu par Deposer.
            http = new HttpClient(new HttpClientHandler { AllowAutoRedirect = false }) { Timeout = Timeout.InfiniteTimeSpan };
        }

        public void Dispose() => http.Dispose();

        public RecuIntention Deposer(string intentionJson)
        {
            // Pas un objet JSON : faute de l'appelant, levée avant tout envoi.
            if (intentionJson == null) throw new ArgumentException("une intention est un objet JSON, reçu null", nameof(intentionJson));
            try { LecteurJson.LireObjet(intentionJson); }
            catch (ErreurJson erreur) { throw new ArgumentException("une intention est un objet JSON : " + erreur.Message, nameof(intentionJson), erreur); }

            string adresse = Hote + ":" + port.ToString(CultureInfo.InvariantCulture);
            int statut;
            string corps;
            using (var minuterie = new CancellationTokenSource())
            using (var contenu = new ByteArrayContent(Encoding.UTF8.GetBytes(intentionJson)) { Headers = { ContentType = new MediaTypeHeaderValue("application/json") } })
            {
                try
                {
                    minuterie.CancelAfter(delai);
                    using (HttpResponseMessage reponse = http.PostAsync("http://" + adresse + "/intention", contenu, minuterie.Token).GetAwaiter().GetResult())
                    {
                        statut = (int)reponse.StatusCode;
                        corps = Encoding.UTF8.GetString(reponse.Content.ReadAsByteArrayAsync().GetAwaiter().GetResult());
                    }
                }
                catch (Exception erreur)
                {
                    // Le runtime peut rendre l'annulation sous plusieurs formes : seule la minuterie fait foi.
                    if (minuterie.IsCancellationRequested)
                        return Absente("délai dépassé (" + delai.TotalMilliseconds.ToString(CultureInfo.InvariantCulture) + " ms) sur " + adresse);
                    return Absente("service absent sur " + adresse + " (" + erreur.GetBaseException().Message + ")");
                }
            }

            if (statut != 200 && statut != 400 && statut != 409) return Absente("statut " + statut + ", corps reçu : " + corps);
            string code = "statut " + statut + " : ";
            Dictionary<string, object> objet;
            try { objet = LecteurJson.LireObjet(corps); }
            catch (ErreurJson erreur) { return Absente(code + erreur.Message); }

            // Le statut et le corps doivent dire la même chose : un 4xx n'est jamais une acceptation.
            bool accepte = statut == 200;
            if (!(Valeur(objet, "acceptee") is bool lu) || lu != accepte)
                return Absente(code + Fautive(objet, "acceptee", accepte ? "true" : "false"));
            // Dès 2^53 un double ne dit plus quel entier le texte portait : refusé plutôt que deviné.
            if (accepte)
                return Valeur(objet, "appliquee_au_tick") is double tick && tick == Math.Floor(tick) && tick >= 0 && tick < 9007199254740992.0
                    ? RecuIntention.AccepteeAu((long)tick) : Absente(code + Fautive(objet, "appliquee_au_tick", "un entier ≥ 0 et < 2^53"));
            return Valeur(objet, "erreur") is string raison && raison.Length > 0
                ? RecuIntention.Refusee(statut, raison) : Absente(code + Fautive(objet, "erreur", "un texte non vide"));
        }

        private static RecuIntention Absente(string cause) => RecuIntention.Absente("intention : " + cause);

        private static object Valeur(Dictionary<string, object> objet, string cle) => objet.TryGetValue(cle, out object valeur) ? valeur : null;

        private static string Fautive(Dictionary<string, object> objet, string cle, string attendu) =>
            !objet.TryGetValue(cle, out object valeur) ? "clé absente : " + cle
            : "clé " + cle + " : " + attendu + " attendu, reçu " + (valeur == null ? "null" : valeur is bool b ? (b ? "true" : "false")
                : valeur is string s ? "le texte \"" + s + "\"" : Convert.ToString(valeur, CultureInfo.InvariantCulture));
    }
}
