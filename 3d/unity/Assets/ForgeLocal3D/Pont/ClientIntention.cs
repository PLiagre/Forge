using System;
using System.Collections.Generic;
using System.Globalization;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;

namespace Forge.Pont
{
    // Le reçu d'une intention tel que `sim/` le rend : acceptée au tick qu'il nomme, refusée avec sa raison, ou absente avec sa cause.
    public sealed class RecuIntention
    {
        public bool Presente => Absence == null;
        public bool Acceptee => AppliqueeAuTick != null;
        public long? AppliqueeAuTick { get; }
        public int? Statut { get; }
        public string Erreur { get; }
        public string Absence { get; }
        private RecuIntention(long? tick, int? statut, string erreur, string absence) { AppliqueeAuTick = tick; Statut = statut; Erreur = erreur; Absence = absence; }
        // `AccepteeAu` et non `Acceptee` : C# refuse une méthode du nom d'une propriété.
        public static RecuIntention AccepteeAu(long tick) => tick >= 0 ? new RecuIntention(tick, 200, null, null) : throw new ArgumentException("un tick ≥ 0 attendu", nameof(tick));
        public static RecuIntention Refusee(int statut, string erreur) => (statut == 400 || statut == 409) && !string.IsNullOrEmpty(erreur)
            ? new RecuIntention(null, statut, erreur, null) : throw new ArgumentException("un refus porte 400 ou 409 et nomme sa raison", nameof(statut));
        public static RecuIntention Absente(string cause) => !string.IsNullOrEmpty(cause) ? new RecuIntention(null, null, null, cause) : throw new ArgumentException("une absence nomme sa cause", nameof(cause));
    }

    // Dépose une intention au service local (`POST /intention` sur 127.0.0.1) et relit son reçu, sans juger ni recalculer.
    public sealed class ClientIntention : IDisposable
    {
        private static readonly Regex Jetons = new Regex(@"""(?:[^""\\]|\\.)*""|[{}\[\]]|:[ \t\n\r]*([-0-9.eE+]*)");
        private readonly string adresse;
        private readonly TimeSpan delai;
        private readonly HttpClient http;

        public ClientIntention(int port, TimeSpan delai)
        {
            if (port < 1 || port > 65535) throw new ArgumentOutOfRangeException(nameof(port), port, "port hors de 1..65535");
            if (delai <= TimeSpan.Zero && delai != Timeout.InfiniteTimeSpan) throw new ArgumentOutOfRangeException(nameof(delai), delai, "un délai positif attendu");
            adresse = "127.0.0.1:" + port.ToString(CultureInfo.InvariantCulture);
            this.delai = delai;
            // Aucune redirection suivie : un 3xx est un statut inattendu. Le délai est tenu par Deposer.
            http = new HttpClient(new HttpClientHandler { AllowAutoRedirect = false }) { Timeout = Timeout.InfiniteTimeSpan };
        }

        public void Dispose() => http.Dispose();

        // Lève ArgumentException si le texte n'est pas un objet JSON ; ne lève jamais pour une cause du service.
        public RecuIntention Deposer(string intentionJson)
        {
            try { LecteurJson.LireObjet(intentionJson ?? throw new ArgumentException("une intention est un objet JSON, reçu null", nameof(intentionJson))); }
            catch (ErreurJson erreur) { throw new ArgumentException("une intention est un objet JSON : " + erreur.Message, nameof(intentionJson), erreur); }
            int statut, profondeur = 0; string corps, cle = null, ecrit = null;
            using (var minuterie = new CancellationTokenSource(delai))
            using (var contenu = new ByteArrayContent(Encoding.UTF8.GetBytes(intentionJson)) { Headers = { ContentType = new MediaTypeHeaderValue("application/json") } })
                try
                {
                    using (HttpResponseMessage reponse = http.PostAsync("http://" + adresse + "/intention", contenu, minuterie.Token).GetAwaiter().GetResult())
                        (statut, corps) = ((int)reponse.StatusCode, Encoding.UTF8.GetString(reponse.Content.ReadAsByteArrayAsync().GetAwaiter().GetResult()));
                }
                catch (Exception erreur) // l'annulation a plusieurs formes selon le runtime : seule la minuterie fait foi
                {
                    return Absente(minuterie.IsCancellationRequested ? "délai dépassé (" + delai.TotalMilliseconds.ToString(CultureInfo.InvariantCulture) + " ms) sur " + adresse
                        : "service absent sur " + adresse + " (" + erreur.GetBaseException().Message + ")");
                }
            if (statut != 200 && statut != 400 && statut != 409) return Absente("statut " + statut + ", corps reçu : " + corps);
            string code = "statut " + statut + " : "; Dictionary<string, object> objet;
            try { objet = LecteurJson.LireObjet(corps); }
            catch (ErreurJson erreur) { return Absente(code + erreur.Message); }
            // Le statut et le corps doivent dire la même chose : un 4xx n'est jamais une acceptation.
            bool accepte = statut == 200;
            if (!(objet.TryGetValue("acceptee", out object lu) && lu is bool dit && dit == accepte))
                return Absente(code + Fautive(objet, "acceptee", accepte ? "true" : "false"));
            if (!accepte)
                return objet.TryGetValue("erreur", out object raison) && raison is string texte && texte.Length > 0
                    ? RecuIntention.Refusee(statut, texte) : Absente(code + Fautive(objet, "erreur", "un texte non vide"));
            // LecteurJson arrondit `7.0000000000000001` en 7 : le tick se relit aussi dans le texte (Jetons : chaînes, accolades, crochets, nombre après `:`), sous la
            // clé de la racine décodée par LecteurJson (échappements compris), en chiffres seuls, < 2^53 et égal à la valeur lue ; sinon refusé.
            foreach (Match j in Jetons.Matches(corps)) if (j.Value == "{" || j.Value == "[") profondeur++; else if (j.Value == "}" || j.Value == "]") profondeur--;
                else if (j.Value[0] == '"') cle = (string)LecteurJson.Lire(j.Value); else if (profondeur == 1 && cle == "appliquee_au_tick") ecrit = j.Groups[1].Value;
            return long.TryParse(ecrit, NumberStyles.None, CultureInfo.InvariantCulture, out long tick) && tick < 9007199254740992L
                && objet.TryGetValue("appliquee_au_tick", out object valeur) && valeur is double d && d == tick
                ? RecuIntention.AccepteeAu(tick) : Absente(code + Fautive(objet, "appliquee_au_tick", "un entier écrit en chiffres, ≥ 0 et < 2^53"));
        }

        private static RecuIntention Absente(string cause) => RecuIntention.Absente("intention : " + cause);
        private static string Fautive(Dictionary<string, object> objet, string cle, string attendu) =>
            objet.TryGetValue(cle, out object valeur) ? "clé " + cle + " : " + attendu + " attendu, reçu " + (valeur == null ? "null" : Convert.ToString(valeur, CultureInfo.InvariantCulture)) : "clé absente : " + cle;
    }
}
