using System;
using System.Collections;
using System.Linq;
using System.Collections.Generic; using System.Globalization; using System.IO; using System.Text.RegularExpressions;
using NUnit.Framework;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;
using UnityEngine.TestTools;
using UnityEditor.TestTools;

namespace Forge.Interface.Tests
{
    public sealed class SocleInterfaceTests
    {
        GameObject galerie;
        EventSystem evenements;

        [SetUp] public void Ouvrir()
        {
            galerie = SocleInterface.Creer();
            evenements = galerie.GetComponentInChildren<EventSystem>();
        }

        [TearDown] public void Fermer() => UnityEngine.Object.DestroyImmediate(galerie);

        [UnityTest] public IEnumerator LaSceneReconstruitSesCommandesEnPlay()
        {
            UnityEngine.Object.DestroyImmediate(galerie);
            yield return new EnterPlayMode();
            galerie = new GameObject("Scène du socle", typeof(SocleInterface));
            yield return null;
            evenements = galerie.GetComponentInChildren<EventSystem>();
            LeClicActifNeFermePasLeDossierVoisin();
            UnityEngine.Object.DestroyImmediate(galerie);
            yield return new ExitPlayMode();
        }

        Button Bouton(string nom)
        {
            var bouton = galerie.GetComponentsInChildren<Button>(true).SingleOrDefault(b => b.name == nom);
            Assert.That(bouton, Is.Not.Null, "bouton absent : " + nom);
            return bouton;
        }

        [Test] public void LesPolicesEmbarqueesDistinguentTitresEtLecture()
        {
            var textes = galerie.GetComponentsInChildren<Text>();
            var titre = textes.First(t => t.fontSize == SocleInterface.Titre);
            var corps = textes.First(t => t.fontSize == SocleInterface.Corps);
            Assert.That(titre.font.name, Is.EqualTo("NotoSerif-Regular"));
            Assert.That(corps.font.name, Is.EqualTo("NotoSans-Regular"));
            foreach (var police in new[] { titre.font, corps.font })
            {
                police.RequestCharactersInTexture("ÉÀÇœéèêùî0123456789", 18);
                foreach (char lettre in "ÉÀÇœéèêùî0123456789")
                    Assert.That(police.HasCharacter(lettre), Is.True, lettre.ToString());
            }
        }

        [Test] public void LeThemeRefuseUnJetonInconnu()
        {
            Assert.Throws<ArgumentException>(() => SocleInterface.Couleur("inconnue"));
            ColorUtility.TryParseHtmlString("#E8DDC9", out var papier);
            Assert.That(SocleInterface.Couleur("papier"), Is.EqualTo(papier));
        }

        [Test] public void DeuxDossiersRestentVisiblesEtLaGalerieEstDeclaree()
        {
            foreach (var nom in new[] { "Le domaine", "Le conseil" })
                Assert.That(galerie.GetComponentsInChildren<Image>().Any(p => p.name == nom), Is.True, nom);
            Assert.That(galerie.GetComponentsInChildren<Text>().Any(t => t.text.Contains("aucune partie chargée")), Is.True);
        }

        [Test] public void LeFocusReelChangeLaCouleurDuBouton()
        {
            var bouton = Bouton("Consulter le dossier");
            var normal = bouton.targetGraphic.canvasRenderer.GetColor();
            evenements.SetSelectedGameObject(bouton.gameObject);
            Assert.That(bouton.targetGraphic.canvasRenderer.GetColor(), Is.Not.EqualTo(normal));
            Assert.That(bouton.GetComponent<Outline>().enabled, Is.True);
            evenements.SetSelectedGameObject(null);
            Assert.That(bouton.GetComponent<Outline>().enabled, Is.False);
        }

        [Test] public void UnBoutonInactifNeDeclencheRien()
        {
            var bouton = Bouton("En attente du monde");
            int appels = 0;
            bouton.onClick.AddListener(() => appels++);
            ExecuteEvents.Execute(bouton.gameObject, new PointerEventData(evenements), ExecuteEvents.pointerClickHandler);
            Assert.That(bouton.interactable, Is.False);
            Assert.That(appels, Is.Zero);
        }

        [Test] public void LeClicActifNeFermePasLeDossierVoisin()
        {
            var bouton = Bouton("Consulter le dossier");
            int appels = 0;
            bouton.onClick.AddListener(() => appels++);
            ExecuteEvents.Execute(bouton.gameObject, new PointerEventData(evenements), ExecuteEvents.pointerClickHandler);
            Assert.That(appels, Is.EqualTo(1));
            Assert.That(galerie.GetComponentsInChildren<Text>().Any(t => t.text.Contains("Aucun ordre envoyé")), Is.True);
            DeuxDossiersRestentVisiblesEtLaGalerieEstDeclaree();
        }

        // Lot #878 : l'infobulle du socle, entière dans l'écran et jamais sur le point survolé.
        static readonly (string nom, string phrase)[] Phrases = { ("Consulter le dossier", "Ouvre le dossier sans rien envoyer au monde."),
            ("En attente du monde", "Indisponible : aucune partie chargée."), ("Parcourir au clavier", "Passe d'une commande à l'autre avec les flèches ; Entrée agit.") };
        const float ARRONDI = 1e-3f; // l'arrondi flottant, en pixels
        Canvas Toile => galerie.GetComponentsInChildren<Canvas>(true).Single(c => c.name == "Documents");
        static Rect Carre(Vector2 p) => new Rect(p.x - 24, p.y - 24, 48, 48);
        static bool Chevauche(Rect r, Vector2 p) => Rect.MinMaxRect(r.xMin + ARRONDI, r.yMin + ARRONDI, r.xMax - ARRONDI, r.yMax - ARRONDI).Overlaps(Carre(p));
        static bool Dedans(Rect r, Rect ecran) => r.xMin >= ecran.xMin - ARRONDI && r.yMin >= ecran.yMin - ARRONDI && r.xMax <= ecran.xMax + ARRONDI && r.yMax <= ecran.yMax + ARRONDI;

        [Test] public void LInfobulleResteEntiereEtLibereLePoint()
        {
            string longue = Phrases.Select(p => p.phrase).OrderByDescending(p => p.Length).First();
            Vector2 unites = Infobulle.Montrer(Toile, longue, Toile.pixelRect.position).rect.size;
            Assert.That(unites.x, Is.GreaterThan(0)); Assert.That(unites.y, Is.GreaterThan(0));
            int juges = 0;
            foreach (var ecran in new[] { new Vector2(1920, 1080), new Vector2(1280, 720) })
            {
                Vector2 taille = unites * (ecran.x / 1920);
                for (int i = 0; i <= ecran.x / 20; i++)
                    for (int j = 0; j <= ecran.y / 20; j++, juges++)
                    {
                        var p = new Vector2(i * 20, j * 20); Rect r = Infobulle.Placer(p, taille, ecran);
                        if (!Dedans(r, new Rect(Vector2.zero, ecran)) || Chevauche(r, p)) Assert.Fail("écran " + ecran + ", point " + p + " : feuillet " + r);
                    }
                Assert.Throws<ArgumentException>(() => Infobulle.Placer(ecran / 2, new Vector2(ecran.x / 2, taille.y), ecran));
                Assert.Throws<ArgumentException>(() => Infobulle.Placer(ecran / 2, new Vector2(taille.x, ecran.y / 2), ecran));
            }
            Assert.That(juges, Is.EqualTo(97 * 55 + 65 * 37), "points jugés");
        }

        [Test] public void UneCommandeRefuseUnePhraseVide()
        {
            Transform domaine = galerie.GetComponentsInChildren<Image>().Single(i => i.name == "Le domaine").transform;
            foreach (var p in new[] { "", "   ", "\n" })
            {
                var refus = Assert.Throws<ArgumentException>(() => SocleInterface.Commande(domaine, "Commande sans phrase", 24, 540, null, true, p));
                StringAssert.Contains("Commande sans phrase", refus.Message);
                Assert.That(domaine.Cast<Transform>().Count(t => t.name == "Commande sans phrase"), Is.Zero, "enfant laissé par « " + p + " »");
            }
            Assert.Throws<ArgumentException>(() => Infobulle.Montrer(Toile, "", Toile.pixelRect.center));
            Assert.That(SocleInterface.Commande(domaine, "Sans phrase", 24, 540, null).GetComponent<Infobulle>(), Is.Null);
            Assert.That(SocleInterface.Commande(domaine, "Avec phrase", 24, 600, null, true, "Fait ceci.").GetComponent<Infobulle>().Phrase, Is.EqualTo("Fait ceci."));
        }

        [Test] public void LaGalerieMontreLInfobulleSurSesCommandes()
        {
            Canvas toile = Toile; Canvas.ForceUpdateCanvases();
            var coins = new Vector3[4];
            foreach (var (nom, phrase) in Phrases)
            {
                var bouton = Bouton(nom); ((RectTransform)bouton.transform).GetWorldCorners(coins);
                Vector2 point = RectTransformUtility.WorldToScreenPoint(null, (coins[0] + coins[2]) / 2);
                ExecuteEvents.Execute(bouton.gameObject, new PointerEventData(evenements) { position = point }, ExecuteEvents.pointerEnterHandler);
                var feuillets = toile.GetComponentsInChildren<RectTransform>().Where(t => t.name == "Infobulle").ToArray();
                Assert.That(feuillets.Length, Is.EqualTo(1), nom);
                Assert.That(feuillets[0].GetComponentInChildren<Text>().text, Is.EqualTo(phrase));
                feuillets[0].GetWorldCorners(coins);
                var ecran = coins.Select(c => RectTransformUtility.WorldToScreenPoint(null, c)).ToArray();
                Rect r = Rect.MinMaxRect(ecran.Min(e => e.x), ecran.Min(e => e.y), ecran.Max(e => e.x), ecran.Max(e => e.y));
                Assert.That(Dedans(r, toile.pixelRect), Is.True, nom + " : feuillet " + r + " hors de " + toile.pixelRect);
                Assert.That(Chevauche(r, point), Is.False, nom + " : feuillet " + r + " sur le point " + point);
                ExecuteEvents.Execute(bouton.gameObject, new PointerEventData(evenements) { position = point }, ExecuteEvents.pointerExitHandler);
                Assert.That(feuillets[0].gameObject.activeSelf, Is.False, nom);
            }
            Assert.That(galerie.GetComponentsInChildren<Canvas>(true).Length, Is.EqualTo(1));
            Assert.That(toile.transform.Find("Infobulle").GetComponentsInChildren<Graphic>(true).Where(g => g.raycastTarget), Is.Empty);
        }

        // Lot #849 : la langue du cabinet — seize jetons, matières sans aléa, registre, neuf états, galerie du registre.
        static readonly CultureInfo Fr = CultureInfo.GetCultureInfo("fr-FR");
        static readonly string[] Matieres = { "pierre", "bois-brule", "metal" };
        static string DA() => File.ReadAllText(Path.GetFullPath(Path.Combine(Application.dataPath, "../../../docs/interface/DA.md")));
        // Les lignes des deux tableaux de jetons de la DA : nom, hex, et la colonne « Contraste mesuré » du second.
        static List<(string nom, string hex, string contraste)> JetonsDeLaDA()
        {
            var lus = new List<(string, string, string)>();
            foreach (string ligne in DA().Split('\n'))
            {
                var m = Regex.Match(ligne, "^\\|\\s*`?([a-z][a-z-]*)`?\\s*\\|\\s*`(#[0-9A-Fa-f]{6})`");
                if (m.Success) { string[] c = ligne.Split('|'); lus.Add((m.Groups[1].Value, m.Groups[2].Value, c.Length >= 6 ? c[4] : "")); }
            }
            return lus;
        }

        [Test] public void LesJetonsSontCeuxDeLaRevision()
        {
            var lus = JetonsDeLaDA(); Assert.That(lus.Count, Is.EqualTo(15), "lignes de jetons lues dans la DA");
            var mer = Regex.Match(DA(), "`mer` \\(`(#[0-9A-Fa-f]{6})`"); Assert.That(mer.Success, Is.True, "le mer de la phrase du pigment");
            lus.Add(("mer", mer.Groups[1].Value, ""));
            Assert.That(SocleInterface.Jetons.Count, Is.EqualTo(16)); CollectionAssert.AreEquivalent(lus.Select(l => l.nom).ToArray(), SocleInterface.Jetons.ToArray());
            foreach (var (nom, hex, _) in lus) { ColorUtility.TryParseHtmlString(hex, out var attendue); Assert.That(SocleInterface.Couleur(nom), Is.EqualTo(attendue), nom); }
        }

        [Test] public void ChaquePaireDeclareeTientSonSeuil()
        {
            Assert.That(SocleInterface.Refuse(SocleInterface.Paires), Is.Null);
            foreach (var p in EtatsDuCabinet.PairesDesEtats()) Assert.That(SocleInterface.Paires.Contains(p), Is.True, p.ToString());
            int lus = 0;
            foreach (var (nom, _, contraste) in JetonsDeLaDA())
                foreach (Match m in Regex.Matches(contraste, "`([a-z-]+)` dessus : (\\d+,\\d):1|sur `([a-z-]+)` : (\\d+,\\d):1"))
                {
                    bool dessus = m.Groups[1].Success; string autre = dessus ? m.Groups[1].Value : m.Groups[3].Value;
                    double dit = double.Parse(dessus ? m.Groups[2].Value : m.Groups[4].Value, Fr), mesure = SocleInterface.Contraste(SocleInterface.Couleur(dessus ? autre : nom), SocleInterface.Couleur(dessus ? nom : autre));
                    Assert.That(Math.Round(mesure, 1, MidpointRounding.AwayFromZero), Is.EqualTo(dit).Within(1e-9), nom + " et " + autre); lus++;
                }
            Assert.That(lus, Is.EqualTo(8), "contrastes lus dans la DA");
            string refus = SocleInterface.Refuse(SocleInterface.Paires.Concat(new[] { ("or-vieilli", "papier", SocleInterface.Usage.Texte) }));
            StringAssert.Contains("or-vieilli sur papier", refus); StringAssert.Contains("2,0:1", refus);
            Assert.Throws<ArgumentException>(() => SocleInterface.Refuse(new[] { ("inconnu", "papier", SocleInterface.Usage.Texte) }));
        }

        [Test] public void ChaqueEtatSeLitSansSaCouleur()
        {
            Assert.That(EtatsDuCabinet.Table.Count, Is.EqualTo(9)); Assert.That(EtatsDuCabinet.Confondus(EtatsDuCabinet.Table), Is.Null);
            foreach (var d in EtatsDuCabinet.Table.Where(d => d.Signe != null))
                foreach (var police in new[] { SocleInterface.Police(true), SocleInterface.Police(false) })
                {
                    police.RequestCharactersInTexture(d.Signe, SocleInterface.Corps);
                    foreach (char c in d.Signe) Assert.That(police.HasCharacter(c), Is.True, d.Nom + " : " + c + " dans " + police.name);
                }
            var repos = EtatsDuCabinet.De(EtatDuCabinet.Repos);
            var teinte = EtatsDuCabinet.Table.Select(d => d.Nom == "reçu" ? new Declaration(d.Nom, d.Matiere, d.Texte, d.Trait, repos.Forme, repos.Epaisseur, repos.Signe, repos.Mot) : d);
            Assert.That(EtatsDuCabinet.Confondus(teinte), Is.EqualTo("repos et reçu ne diffèrent que par leur teinte"));
        }

        static bool Egal(Color32 a, Color32 b, int ecart = 0) => Mathf.Abs(a.r - b.r) <= ecart && Mathf.Abs(a.g - b.g) <= ecart && Mathf.Abs(a.b - b.b) <= ecart && Mathf.Abs(a.a - b.a) <= ecart;
        // Ce qui ne va pas dans le générateur d'une matière, ou null : mêmes octets malgré le hasard, moyenne au jeton, grain entre 1 et 8, papier lisible sur chaque pixel.
        static string DefautDeMatiere(Func<string, Color32[]> fabrique, string matiere)
        {
            UnityEngine.Random.InitState(1); var a = fabrique(matiere); UnityEngine.Random.InitState(2); var b = fabrique(matiere);
            if (a == null || a.Length == 0 || b == null || a.Length != b.Length) return matiere + " : aucun pixel";
            for (int i = 0; i < a.Length; i++) if (!Egal(a[i], b[i])) return matiere + " : le pixel " + i + " dépend du hasard";
            Color jeton = SocleInterface.Couleur(matiere) * 255f; double somme = 0, carres = 0, r = 0, g = 0, bleu = 0;
            foreach (var p in a)
            {
                r += p.r; g += p.g; bleu += p.b; double lum = .2126 * p.r + .7152 * p.g + .0722 * p.b; somme += lum; carres += lum * lum;
                if (SocleInterface.Contraste(SocleInterface.Couleur("papier"), p) < 4.5) return matiere + " : papier sous 4,5:1 sur un pixel";
            }
            int n = a.Length; double ecart = Math.Sqrt(Math.Max(0, carres / n - (somme / n) * (somme / n)));
            if (Math.Abs(r / n - jeton.r) > 3 || Math.Abs(g / n - jeton.g) > 3 || Math.Abs(bleu / n - jeton.b) > 3) return matiere + " : moyenne (" + r / n + ", " + g / n + ", " + bleu / n + ") loin du jeton " + jeton;
            return ecart < 1 || ecart > 8 ? matiere + " : écart-type de luminance " + ecart + " hors de 1 à 8" : null;
        }

        [Test] public void LesMatieresNaissentSansAlea()
        {
            foreach (string m in Matieres) Assert.That(DefautDeMatiere(MatieresCabinet.Pixels, m), Is.Null);
            Assert.That(DefautDeMatiere(m => Enumerable.Range(0, 128 * 128).Select(_ => (Color32)new Color(UnityEngine.Random.value, UnityEngine.Random.value, UnityEngine.Random.value)).ToArray(), "pierre"), Does.Contain("hasard"), "contre-épreuve : un générateur au hasard");
            Assert.That(DefautDeMatiere(m => Enumerable.Repeat((Color32)SocleInterface.Couleur(m), 128 * 128).ToArray(), "metal"), Does.Contain("écart-type"), "contre-épreuve : un aplat du jeton");
            Assert.Throws<ArgumentException>(() => MatieresCabinet.Pixels("papier")); Assert.Throws<ArgumentException>(() => MatieresCabinet.Pixels("inconnue"));
            foreach (var s in new[] { MatieresCabinet.Pierre, MatieresCabinet.BoisBrule, MatieresCabinet.Metal }) Assert.That(s, Is.Not.Null);
            Assert.That(MatieresCabinet.Pierre, Is.SameAs(MatieresCabinet.Pierre));
            var feuillet = MatieresCabinet.FeuilletDInfobulle.texture; var px = feuillet.GetPixels32(); int e = EtatsDuCabinet.De(EtatDuCabinet.Survol).Epaisseur, c = feuillet.width;
            for (int y = 0; y < c; y++) for (int x = 0; x < c; x++)
                    Assert.That(Egal(px[y * c + x], SocleInterface.Couleur("cuivre"), 1), Is.EqualTo(Mathf.Min(x, y, c - 1 - x, c - 1 - y) < e), "texel " + x + ", " + y + " du feuillet d'infobulle");
        }

        // Un refus sans enfant laissé : la garde passe avant la création.
        static string SansEnfant(Transform parent, Action refuse)
        {
            int avant = parent.childCount;
            try { refuse(); return "aucune exception"; } catch (ArgumentException) { return parent.childCount == avant ? null : "enfant laissé après le refus"; }
        }

        [Test] public void LeRegistreRefuseCeQuiManque()
        {
            var f = (RectTransform)new GameObject("Feuillet d'essai", typeof(RectTransform)).transform; f.SetParent(galerie.transform, false);
            var rubrique = SocleInterface.Rubrique(f, "Le grenier", 24, 20, 800);
            Assert.That(rubrique.text, Is.EqualTo(string.Join(" ", "LE GRENIER".Select(c => c.ToString()))));
            Assert.That(rubrique.font.name, Is.EqualTo("NotoSerif-Regular")); Assert.That(rubrique.fontSize, Is.EqualTo(SocleInterface.Titre));
            Assert.That(rubrique.color, Is.EqualTo(SocleInterface.Couleur("sang"))); Assert.That(SocleInterface.Rubrique(f, "Sombre", 0, 0, 800, true).color, Is.EqualTo(SocleInterface.Couleur("papier")));
            var filets = f.Cast<RectTransform>().Where(t => t.name == "Filet").Take(2).OrderBy(t => -t.anchoredPosition.y).ToArray();
            Assert.That(filets.Length, Is.EqualTo(2));
            foreach (var filet in filets) { Assert.That(filet.sizeDelta.y, Is.EqualTo(1f)); Assert.That(filet.GetComponent<Image>().color, Is.EqualTo(SocleInterface.Couleur("metal"))); }
            Assert.That(filets[0].anchoredPosition.y - filets[1].anchoredPosition.y, Is.EqualTo(4f), "1 px de filet, puis 3 px d'écart");
            Text Valeur(RectTransform l) => l.GetComponentsInChildren<Text>().Single(t => t.name == "Valeur");
            var absente = SocleInterface.LigneDeCompte(f, "Exemple absent", null, "kg", 24, 100, 800);
            StringAssert.StartsWith("— Donnée absente", Valeur(absente).text); StringAssert.DoesNotContain("0", Valeur(absente).text);
            var compte = SocleInterface.LigneDeCompte(f, "Exemple de compte", 1250m, "kg", 24, 140, 800);
            Assert.That(Valeur(compte).text, Is.EqualTo("1250 kg")); Assert.That(Valeur(compte).alignment, Is.EqualTo(TextAnchor.UpperRight));
            Assert.That(compte.GetComponentsInChildren<Text>().Single(t => t.name == "Libellé").color, Is.EqualTo(SocleInterface.Couleur("encre")));
            var refus = new (string, Action)[] { ("libellé vide", () => SocleInterface.LigneDeCompte(f, "", 1m, "kg", 0, 0, 800)), ("unité vide", () => SocleInterface.LigneDeCompte(f, "Compte", 1m, " ", 0, 0, 800)),
                ("date vide", () => SocleInterface.PiedDeFeuillet(f, "", 0, 0, 800)), ("note à nombre", () => SocleInterface.NoteEnMarge(f, "3 sacs", 0, 0, 800)) };
            foreach (var (nom, action) in refus) Assert.That(SansEnfant(f, action), Is.Null, nom);
            Assert.That(SansEnfant(f, () => { new GameObject("Trop tard", typeof(RectTransform)).transform.SetParent(f, false); throw new ArgumentException(); }), Is.EqualTo("enfant laissé après le refus"), "contre-épreuve : une garde après la création");
            Assert.That(SocleInterface.PiedDeFeuillet(f, "Exemple, aucun tick reçu", 0, 0, 800).color, Is.EqualTo(SocleInterface.Couleur("secondaire")));
            var note = SocleInterface.NoteEnMarge(f, "La cause se dit en marge.", 0, 0, 800); Assert.That(note.fontSize, Is.EqualTo(16)); Assert.That(note.color, Is.EqualTo(SocleInterface.Couleur("secondaire")));
            var sep = SocleInterface.Separateur(f, 24, 300, 800); var losanges = sep.Cast<RectTransform>().Where(t => t.name == "Losange").ToArray();
            Assert.That(losanges.Length, Is.EqualTo(1)); Assert.That(losanges[0].sizeDelta, Is.EqualTo(new Vector2(8, 8)));
            Assert.That(Mathf.DeltaAngle(losanges[0].localEulerAngles.z, 45), Is.EqualTo(0).Within(.01f)); Assert.That(sep.Cast<Transform>().Count(t => t.name == "Filet"), Is.EqualTo(1));
            var sceau = SocleInterface.Sceau(f, 0, 0); Assert.That(sceau.rectTransform.sizeDelta, Is.EqualTo(new Vector2(28, 28))); Assert.That(sceau.raycastTarget, Is.False);
            Color32 sang = SocleInterface.Couleur("sang"); double rouge = 0, vert = 0, bleu = 0; int opaques = 0;
            foreach (var p in sceau.sprite.texture.GetPixels32().Where(p => p.a == 255)) { rouge += p.r; vert += p.g; bleu += p.b; opaques++; }
            Assert.That(opaques, Is.GreaterThan(1000)); Assert.That(Math.Max(Math.Abs(rouge / opaques - sang.r), Math.Max(Math.Abs(vert / opaques - sang.g), Math.Abs(bleu / opaques - sang.b))), Is.LessThan(12), "moyenne de la cire");
        }

        // Ce qui ne va pas dans une plaque d'état, ou null : son signe, son mot, ses barres de trait et leur épaisseur.
        static string DefautDePlaque(RectTransform plaque, Declaration d)
        {
            string dit = plaque.GetComponentInChildren<Text>().text;
            if (d.Signe != null && !dit.Contains(d.Signe)) return d.Nom + " : le signe « " + d.Signe + " » manque dans « " + dit + " »";
            if (d.Mot != null && !dit.Contains(d.Mot)) return d.Nom + " : le mot « " + d.Mot + " » manque dans « " + dit + " »";
            var barres = plaque.Cast<RectTransform>().Where(t => t.name == "Trait" || t.name == "Tiret").ToArray(); int n = barres.Length;
            string nom = d.Forme == FormeDuTrait.Pointille ? "Tiret" : "Trait";
            bool bon = (d.Forme == FormeDuTrait.Plein ? n == 4 : d.Forme == FormeDuTrait.Double ? n == 8 : d.Forme == FormeDuTrait.Pointille ? n >= 8 : n == 0) && barres.All(t => t.name == nom);
            if (!bon) return d.Nom + " : " + n + " barre(s) pour un trait " + d.Forme;
            return barres.Any(t => !Mathf.Approximately(Mathf.Min(t.rect.width, t.rect.height), d.Epaisseur)) ? d.Nom + " : une barre n'a pas l'épaisseur " + d.Epaisseur : null;
        }
        static Rect DansLeFond(RectTransform fond, RectTransform r)
        {
            var c = new Vector3[4]; r.GetWorldCorners(c); var l = c.Select(v => (Vector2)fond.InverseTransformPoint(v)).ToArray();
            return Rect.MinMaxRect(l.Min(p => p.x), l.Min(p => p.y), l.Max(p => p.x), l.Max(p => p.y));
        }

        [Test] public void LaGalerieDuRegistreMontreTout()
        {
            var registre = GalerieDuRegistre.Creer();
            try
            {
                Assert.That(registre.GetComponentsInChildren<Canvas>(true).Length, Is.EqualTo(1)); Assert.That(registre.GetComponentInChildren<Canvas>(true).name, Is.EqualTo("Registre"));
                var objets = registre.GetComponentsInChildren<RectTransform>(true); var fond = objets.Single(o => o.name == "Fond");
                void Un(string nom) => Assert.That(objets.Count(o => o.name == nom), Is.EqualTo(1), nom);
                foreach (string j in SocleInterface.Jetons) Un("Jeton " + j);
                foreach (string m in Matieres) Un("Matière " + m);
                foreach (string nom in new[] { "Rubrique", "Ligne Exemple de compte", "Ligne Exemple absent", "Note en marge", "Séparateur", "Sceau" }) Un(nom);
                var coin = (RectTransform)registre.GetComponentsInChildren<Button>(true).Single(b => b.name == "Coin de l'écran").transform; // le texte de la commande porte le même nom
                Assert.That(registre.GetComponentsInChildren<Text>().Any(t => t.text.Contains("aucune partie chargée")), Is.True);
                foreach (var d in EtatsDuCabinet.Table) Assert.That(DefautDePlaque(objets.Single(o => o.name == "État " + d.Nom), d), Is.Null);
                foreach (var o in objets.Where(o => o.IsChildOf(fond)))
                {
                    Rect r = DansLeFond(fond, o), page = fond.rect;
                    Assert.That(r.xMin >= page.xMin - .5f && r.yMin >= page.yMin - .5f && r.xMax <= page.xMax + .5f && r.yMax <= page.yMax + .5f, Is.True, o.name + " " + r + " hors de " + page);
                }
                void Tiennent(string ou)
                {
                    foreach (var t in registre.GetComponentsInChildren<Text>())
                    {
                        Assert.That(t.preferredHeight, Is.LessThanOrEqualTo(t.rectTransform.rect.height + .5f), ou + " : hauteur de « " + t.text + " »");
                        if (t.horizontalOverflow == HorizontalWrapMode.Overflow) Assert.That(t.preferredWidth, Is.LessThanOrEqualTo(t.rectTransform.rect.width + .5f), ou + " : largeur de « " + t.text + " »");
                    }
                }
                Tiennent("à l'échelle de l'écran");
                var mise = registre.GetComponentInChildren<CanvasScaler>(); mise.uiScaleMode = CanvasScaler.ScaleMode.ConstantPixelSize; mise.scaleFactor = 2f / 3; Canvas.ForceUpdateCanvases();
                Tiennent("à 1280 × 720 (échelle 2/3)"); mise.scaleFactor = 1; Canvas.ForceUpdateCanvases(); Tiennent("à 1920 × 1080 (échelle 1)");
                var zones = new[] { "Zone titre", "Zone jetons", "Zone matières", "Feuillet du registre", "Zone états", "Zone pied" }.Select(n => DansLeFond(fond, objets.Single(o => o.name == n))).Append(DansLeFond(fond, coin)).ToArray();
                for (int i = 0; i < zones.Length; i++) for (int j = i + 1; j < zones.Length; j++)
                        Assert.That(Rect.MinMaxRect(zones[i].xMin + .5f, zones[i].yMin + .5f, zones[i].xMax - .5f, zones[i].yMax - .5f).Overlaps(zones[j]), Is.False, "zones " + i + " et " + j + " : " + zones[i] + " " + zones[j]);
                for (int i = 1; i < zones.Length - 1; i++) Assert.That(zones[i].yMax, Is.LessThan(zones[i - 1].yMax), "les zones descendent : " + i);
                var attente = objets.Single(o => o.name == "État attente"); var tirets = attente.Cast<Transform>().Where(t => t.name == "Tiret").ToArray();
                var plein = EtatsDuCabinet.De(EtatDuCabinet.Attente); var sansMot = attente.GetComponentInChildren<Text>(); string texte = sansMot.text;
                sansMot.text = texte.Replace(plein.Mot, "");
                Assert.That(DefautDePlaque(attente, plein), Does.Contain("mot"), "contre-épreuve : un mot retiré"); sansMot.text = texte;
                foreach (var t in tirets) UnityEngine.Object.DestroyImmediate(t.gameObject);
                for (int i = 0; i < 4; i++) new GameObject("Trait", typeof(RectTransform)).transform.SetParent(attente, false);
                Assert.That(DefautDePlaque(attente, plein), Does.Contain("barre"), "contre-épreuve : un pointillé réduit à un trait plein");
            }
            finally { UnityEngine.Object.DestroyImmediate(registre); }
        }

        [Test] public void LInfobulleDUnObjetAuCoinResteEntiere()
        {
            var registre = GalerieDuRegistre.Creer();
            try
            {
                Canvas toile = registre.GetComponentInChildren<Canvas>(true);
                string longue = registre.GetComponentsInChildren<Infobulle>(true).Select(i => i.Phrase).OrderByDescending(p => p.Length).First();
                var feuillet = Infobulle.Montrer(toile, longue, toile.pixelRect.position);
                Assert.That(feuillet.GetComponent<Image>().sprite, Is.SameAs(MatieresCabinet.FeuilletDInfobulle));
                Assert.That(feuillet.GetComponentsInChildren<Graphic>(true).Where(g => g.raycastTarget), Is.Empty);
                Vector2 unites = feuillet.rect.size; int cas = 0;
                foreach (var ecran in new[] { new Vector2(1920, 1080), new Vector2(1280, 720) })
                {
                    float echelle = ecran.x / 1920; Vector2 objet = new Vector2(340, 44) * echelle, taille = unites * echelle;
                    foreach (var coin in new[] { Vector2.zero, Vector2.right, Vector2.up, Vector2.one })
                    {
                        var carre = new Rect(Vector2.Scale(ecran - objet, coin), objet); Vector2 p = carre.center; Rect r = Infobulle.Placer(p, taille, ecran); cas++;
                        Assert.That(Dedans(r, new Rect(Vector2.zero, ecran)), Is.True, "écran " + ecran + " coin " + coin + " : feuillet " + r);
                        Assert.That(Rect.MinMaxRect(r.xMin + ARRONDI, r.yMin + ARRONDI, r.xMax - ARRONDI, r.yMax - ARRONDI).Overlaps(carre), Is.False, "écran " + ecran + " coin " + coin + " : feuillet " + r + " sur l'objet " + carre);
                        Assert.That(new Rect(p, taille).Overlaps(carre), Is.True, "contre-épreuve : sans l'écart de 24 px, le feuillet chevauche l'objet");
                    }
                }
                Assert.That(cas, Is.EqualTo(8));
            }
            finally { UnityEngine.Object.DestroyImmediate(registre); }
        }
    }
}
