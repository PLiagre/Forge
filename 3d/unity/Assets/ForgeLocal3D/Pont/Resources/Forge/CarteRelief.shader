// Le terrain de la carte, d'un seul tenant. La teinte de chaque lieu se lit dans la palette par le numéro de son
// texel, et son pays dans la table des pays à la même case. Les traits ne viennent pas de la grille mais des distances
// mesurées aux côtés servis (`_Bords`, `_Frontieres`) : entre quatre texels voisins, la distance signée à un bord se lit
// comme une pente, et le trait se pose là où elle s'annule, large d'un nombre de pixels choisi. Un bord de lieu, une
// côte, une frontière restent donc des traits nets à tout zoom, jamais un escalier. Du sol vers le dessus : la teinte,
// le liseré du pays le long de sa frontière, le bord des lieux, la frontière, les lignes d'eau au large du rivage, la
// côte. `_ForceDesPays` à 0 efface le liseré et la frontière sans rien remesurer : le terrain nu. Le bord des lieux est un trait léger de près, qui s'efface quand un pixel couvre plus de `BORD_LOIN_KM` : de
// loin, seules les frontières et la côte restent.
// Le relief ombre la terre d'une lumière fixe du nord-ouest et pâlit les cimes ; la mer s'éclaircit vers le rivage et
// rend au large la couleur exacte de `_Mer`, celle du fond de la caméra. Rien n'est éclairé par la scène : la carte
// est mate. La lumière est un peu chaude sur les versants éclairés, un peu froide dans l'ombre. De près, quand un pixel
// couvre moins d'un km, un grain fin anime le relief, plus fort sur les pentes : sans lui le relief, levé tous les
// deux km, se lit comme un flou. La mer hors de la carte (`_HorsCarte`, au-delà d'une coupe de la terre) est un papier
// qui s'estompe vers la mer du large, sans côte ni lignes d'eau le long de la coupe ; la terre proche d'une coupe
// (`_Estompe`) s'efface dans ce papier, sans trait droit. Hors de [0, 1], les uv de la jupe lisent le bord des grilles. `_ParAltitude` à 1 teint la terre
// par l'altitude du relief, de palier en palier (`_Palier0` à `_Palier4`, posés à `_Socles` et `_DernierSocle`), au lieu
// de la palette ; un éclat, dont la case de palette est moins opaque, se voit toujours. `_ForceDesLiseres` à 0 efface le
// liseré des pays sans effacer leurs frontières. La cellule marquée (`_LieuxMarques`, ses numéros de texel) est cernée
// d'un trait tiré de `_Marque`, la distance à ses côtés, côte comprise, par-dessus tout le reste. Le terrain se dessine
// avant tout le reste de la carte : les noms des pays s'impriment sur lui, puis viennent les objets posés dessus.
Shader "Forge/CarteRelief"
{
    Properties
    {
        [NoScaleOffset] _Lieux("Lieux", 2D) = "black" {}
        [NoScaleOffset] _Palette("Palette", 2D) = "black" {}
        [NoScaleOffset] _Relief("Relief", 2D) = "black" {}
        [NoScaleOffset] _Bords("Distances au bord du lieu et à la côte", 2D) = "white" {}
        [NoScaleOffset] _Frontieres("Distances à la frontière", 2D) = "white" {}
        [NoScaleOffset] _Pays("Pays de chaque lieu", 2D) = "black" {}
        [NoScaleOffset] _TeintesDesPays("Teinte de chaque pays", 2D) = "black" {}
        _Mer("Mer au large", Color) = (0.08, 0.16, 0.3, 1)
        _Rivage("Mer au rivage", Color) = (0.2, 0.3, 0.42, 1)
        _Roche("Cimes", Color) = (0.85, 0.83, 0.78, 1)
        _EncreDesCotes("Encre des côtes", Color) = (0.1, 0.08, 0.06, 1)
        _EncreDesBords("Encre des bords de lieux", Color) = (0.1, 0.08, 0.06, 1)
        _EncreDesFrontieres("Encre des frontières", Color) = (0.1, 0.08, 0.06, 1)
        _EncreDesEaux("Encre des lignes d'eau", Color) = (0.5, 0.6, 0.7, 1)
        _Pas("Pas des lieux, en km", Float) = 1
        _PorteeDesBords("Portée des distances aux bords, en km", Float) = 12
        _PorteeDesFrontieres("Portée des distances aux frontières, en km", Float) = 16
        _PasDuRelief("Pas du relief, en km", Float) = 2
        _Fond("Fond de la mer, en km", Float) = 6
        _Plafond("Plus haute cime, en km", Float) = 40
        _Vigueur("Vigueur de l'ombre", Float) = 1.6
        _Grain("Force du grain de près", Float) = 1
        _ForceDesPays("Force du liseré et des frontières des pays : 0 les efface", Float) = 1
        _ForceDesLiseres("Force du liseré des pays seul : 0 l'efface", Float) = 1
        [NoScaleOffset] _HorsCarte("Mer hors de la carte, et proximité à la coupe", 2D) = "black" {}
        _Papier("Papier hors de la carte", Color) = (0.85, 0.83, 0.78, 1)
        [NoScaleOffset] _Estompe("Proximité de la terre à une coupe", 2D) = "black" {}
        _ParAltitude("Teinte par l'altitude : 1 au lieu de la palette", Float) = 0
        _Palier0("Teinte du premier palier", Color) = (0.4, 0.5, 0.4, 1)
        _Palier1("Teinte du deuxième palier", Color) = (0.5, 0.6, 0.4, 1)
        _Palier2("Teinte du troisième palier", Color) = (0.6, 0.6, 0.4, 1)
        _Palier3("Teinte du quatrième palier", Color) = (0.55, 0.45, 0.35, 1)
        _Palier4("Teinte du dernier palier", Color) = (0.85, 0.85, 0.85, 1)
        _Socles("Altitude des quatre premiers paliers, en km", Vector) = (0.3, 1.2, 5, 14)
        _DernierSocle("Altitude du dernier palier, en km", Float) = 26
        [NoScaleOffset] _Marque("Distances au bord de la cellule marquée", 2D) = "white" {}
        _PorteeDeLaMarque("Portée des distances à la marque, en km", Float) = 16
        _LieuxMarques("Premier et dernier numéros de texel de la cellule marquée ; -1 sans marque", Vector) = (-1, -1, 0, 0)
        _CouleurDeLaMarque("Couleur du trait de la marque", Color) = (0.1, 0.08, 0.06, 1)
    }
    SubShader
    {
        Tags { "RenderType" = "Opaque" "RenderPipeline" = "UniversalPipeline" "Queue" = "Geometry-10" }
        HLSLINCLUDE
        #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
        CBUFFER_START(UnityPerMaterial)
            float4 _Lieux_TexelSize, _Palette_TexelSize, _Relief_TexelSize;
            float4 _Mer, _Rivage, _Roche, _EncreDesCotes, _EncreDesBords, _EncreDesFrontieres, _EncreDesEaux;
            float4 _Papier, _Palier0, _Palier1, _Palier2, _Palier3, _Palier4, _Socles, _LieuxMarques, _CouleurDeLaMarque;
            float _Pas, _PorteeDesBords, _PorteeDesFrontieres, _PasDuRelief, _Fond, _Plafond, _Vigueur, _Grain, _ForceDesPays;
            float _ForceDesLiseres, _ParAltitude, _DernierSocle, _PorteeDeLaMarque;
        CBUFFER_END
        struct A { float3 p : POSITION; float2 uv : TEXCOORD0; };
        struct V { float4 clip : SV_POSITION; float2 uv : TEXCOORD0; };
        V Vert(A a) { V o; o.clip = TransformObjectToHClip(a.p); o.uv = a.uv; return o; }
        ENDHLSL
        Pass
        {
            Name "Carte" Tags { "LightMode" = "UniversalForward" }
            Cull Off
            HLSLPROGRAM
            #pragma target 4.5
            #pragma vertex Vert
            #pragma fragment Frag
            TEXTURE2D(_Lieux); TEXTURE2D(_Palette); TEXTURE2D(_Relief); SAMPLER(sampler_Relief);
            TEXTURE2D(_Bords); TEXTURE2D(_Frontieres); TEXTURE2D(_Pays); TEXTURE2D(_TeintesDesPays); TEXTURE2D(_HorsCarte); TEXTURE2D(_Estompe); TEXTURE2D(_Marque);
            static const float3 LUMIERE = float3(-0.5145, 0.686, 0.5145); // du nord-ouest, à mi-hauteur
            // En km : sous ce plancher, un texel posé sur un bord ne dit plus de quel côté il est.
            static const float PLANCHER = 0.02;
            // Le liseré d'un pays s'efface sur dix-huit pixels, entre deux km et demi et quatorze ; la frontière et la
            // côte ont une demi-largeur en km, et jamais moins que leur demi-largeur en pixels.
            static const float LISERE_PX = 18.0, LISERE_MIN_KM = 2.5, LISERE_MAX_KM = 14.0, FORCE_DU_LISERE = 0.8;
            static const float FRONTIERE_KM = 0.3, FRONTIERE_PX = 1.1, COTE_KM = 0.18, COTE_PX = 0.7, BORD_PX = 0.5;
            // Le bord des lieux : sa force de près, et les km par pixel où il commence à s'effacer, puis a disparu.
            static const float BORD_PRES = 0.45, BORD_PRES_KM = 0.35, BORD_LOIN_KM = 1.4;
            // Les lignes d'eau, en km du rivage, et ce que chacune couvre de la mer ; elles s'effacent quand un pixel
            // dépasse le km, où elles se toucheraient.
            static const float3 EAUX_KM = float3(2.5, 5.5, 9.0), EAUX = float3(0.34, 0.22, 0.12);

            // Le trait de la marque : sa demi-largeur en km, jamais moins qu'en pixels. Le papier hors de la carte : la part de
            // la mer du large qu'il a pris au plus loin de la coupe.
            static const float MARQUE_KM = 0.6, MARQUE_PX = 1.6, PAPIER_AU_LARGE = 0.55;
            // La lumière des versants éclairés et celle de l'ombre.
            static const float3 CHAUDE = float3(1.05, 1.0, 0.93), FROIDE = float3(0.9, 0.95, 1.05);

            float Altitude(float2 uv) { return SAMPLE_TEXTURE2D(_Relief, sampler_Relief, uv).r; }

            // La teinte d'altitude : fondue d'un palier à l'autre entre leurs socles, celle du premier en dessous, du dernier au-dessus.
            float3 TeinteDAltitude(float h)
            {
                float3 c = _Palier0.rgb;
                c = lerp(c, _Palier1.rgb, saturate((h - _Socles.x) / (_Socles.y - _Socles.x)));
                c = lerp(c, _Palier2.rgb, saturate((h - _Socles.y) / (_Socles.z - _Socles.y)));
                c = lerp(c, _Palier3.rgb, saturate((h - _Socles.z) / (_Socles.w - _Socles.z)));
                return lerp(c, _Palier4.rgb, saturate((h - _Socles.w) / (_DernierSocle - _Socles.w)));
            }
            // La teinte d'un lieu de terre : celle de sa case de palette, ou celle de l'altitude, sauf sous un éclat.
            float3 TeinteDuLieu(float4 caseDePalette, float3 altitude)
            {
                bool eclat = caseDePalette.a < 0.95;
                return _ParAltitude > 0.5 && !eclat ? altitude : caseDePalette.rgb;
            }

            // Un nombre de 0 à 1 par case d'une grille, toujours le même pour la même case ; puis un bruit lisse entre
            // ces nombres, et le grain : deux bruits, l'un de 1,7 km, l'autre de 600 m.
            float Hasard(float2 p)
            {
                uint2 q = (uint2)(int2)floor(p); uint h = q.x * 0x9E3779B1u ^ q.y * 0x85EBCA77u;
                h ^= h >> 15; h *= 0x2C1B3C6Du; h ^= h >> 12;
                return (h & 0xFFFFFFu) / 16777216.0;
            }
            float Bruit(float2 p)
            {
                float2 i = floor(p), f = frac(p); f = f * f * (3.0 - 2.0 * f);
                return lerp(lerp(Hasard(i), Hasard(i + float2(1, 0)), f.x), lerp(Hasard(i + float2(0, 1)), Hasard(i + float2(1, 1)), f.x), f.y);
            }
            float Grain(float2 km) { return 0.6 * Bruit(km / 1.7) + 0.4 * Bruit(km / 0.6 + 17.3); }

            // Une distance signée lue entre quatre texels : telle que les texels la disent, puis rapportée à sa pente, en
            // km et en pixels, et ce que vaut un pixel le long de cette pente. Près du bord, la pente redresse ce que les
            // coins et le plancher faussent, et le trait s'y pose ; au loin elle ne ferait qu'amplifier le grain des
            // distances, et une bande ou une ligne d'eau se lit sur la distance telle quelle.
            struct Lecture { float brute, km, px, pixel; };
            Lecture Lire(float s[4], float poids[4], float2 f, float2 dx, float2 dy)
            {
                float v = s[0] * poids[0] + s[1] * poids[1] + s[2] * poids[2] + s[3] * poids[3];
                float2 g = float2(lerp(s[1] - s[0], s[3] - s[2], f.y), lerp(s[2] - s[0], s[3] - s[1], f.x)) / _Pas;
                float pente = length(g); float2 n = g / max(pente, 1e-5);
                Lecture l; l.brute = v; l.km = v / max(pente, 0.2); // une pente de 1 loin des coins ; à plat, le bord est loin
                l.pixel = max(length(float2(dot(n, dx), dot(n, dy))), 1e-6); l.px = l.km / l.pixel;
                return l;
            }
            // Ce que couvre un trait de cette demi-largeur, à cette distance de son axe, en pixels.
            float Trait(float distance, float demi) { return 1.0 - smoothstep(demi - 0.5, demi + 0.5, distance); }

            half4 Frag(V i) : SV_Target
            {
                // Les quatre texels autour du point, le poids de chacun, et ce que chaque grille dit d'eux.
                float2 p = i.uv * _Lieux_TexelSize.zw - 0.5, base = floor(p), f = p - base;
                int2 dernier = int2(_Lieux_TexelSize.zw) - 1; uint largeurPalette = (uint)_Palette_TexelSize.z;
                float poids[4] = { (1 - f.x) * (1 - f.y), f.x * (1 - f.y), (1 - f.x) * f.y, f.x * f.y };
                float numero[4], pays[4], bord[4], cote[4], frontiere[4], marque[4], s[4], vote[4]; float4 teinte[4];
                int k, a;
                for (k = 0; k < 4; k++)
                {
                    int2 q = clamp(int2(base) + int2(k & 1, k >> 1), int2(0, 0), dernier);
                    numero[k] = round(LOAD_TEXTURE2D(_Lieux, q).r * 65535.0);
                    uint n = (uint)numero[k]; int2 rangee = int2(n % largeurPalette, n / largeurPalette);
                    teinte[k] = LOAD_TEXTURE2D(_Palette, rangee);
                    pays[k] = round(LOAD_TEXTURE2D(_Pays, rangee).r * 65535.0);
                    float2 b = LOAD_TEXTURE2D(_Bords, q).rg; float v = LOAD_TEXTURE2D(_Frontieres, q).r;
                    bord[k] = max(_PorteeDesBords * b.r * b.r, PLANCHER); cote[k] = _PorteeDesBords * b.g * b.g;
                    frontiere[k] = _PorteeDesFrontieres * v * v;
                    float m = LOAD_TEXTURE2D(_Marque, q).r; marque[k] = _PorteeDeLaMarque * m * m;
                }
                // Le point, en km de la carte, et ce qu'un pixel de l'écran en couvre.
                float2 km = i.uv * _Lieux_TexelSize.zw * _Pas, dx = ddx(km), dy = ddy(km);
                float kmParPixel = max(max(length(dx), length(dy)), 1e-6);

                // Le lieu du point : celui dont la distance signée à son bord, lue entre les quatre texels, est la
                // plus grande ; le suivant est celui d'en face, et quand les quatre texels sont du même lieu, il n'a
                // pas de voisin ici.
                for (a = 0; a < 4; a++)
                {
                    vote[a] = 0;
                    for (k = 0; k < 4; k++) vote[a] += poids[k] * bord[k] * (numero[k] == numero[a] ? 1.0 : -1.0);
                }
                int ici = 0;
                for (a = 1; a < 4; a++) if (vote[a] > vote[ici]) ici = a;
                float leNumero = numero[ici], meilleur = -1e9; int enFace = ici;
                for (a = 0; a < 4; a++) if (numero[a] != leNumero && vote[a] > meilleur) { enFace = a; meilleur = vote[a]; }
                bool voisine = enFace != ici;
                for (k = 0; k < 4; k++) s[k] = bord[k] * (numero[k] == leNumero ? 1.0 : -1.0);
                Lecture auBord = Lire(s, poids, f, dx, dy);

                float h = Altitude(i.uv); float2 t = _Relief_TexelSize.xy;
                float2 pente = float2(Altitude(i.uv + float2(t.x, 0)) - Altitude(i.uv - float2(t.x, 0)), Altitude(i.uv + float2(0, t.y)) - Altitude(i.uv - float2(0, t.y))) / (2.0 * _PasDuRelief);
                // De près, le grain ajoute sa pente à celle du relief, à terre seulement, d'autant plus que le relief est pentu.
                float pres = (1.0 - smoothstep(0.2, 0.8, kmParPixel)) * step(0.0, h) * _Grain;
                if (pres > 0.0)
                {
                    const float E = 0.3;
                    float2 grain = float2(Grain(km + float2(E, 0)) - Grain(km - float2(E, 0)), Grain(km + float2(0, E)) - Grain(km - float2(0, E))) / (2.0 * E);
                    pente += grain * pres * (0.08 + 0.5 * saturate(length(pente)));
                }
                float3 normale = normalize(float3(-pente.x * _Vigueur, 1.0, -pente.y * _Vigueur));
                float eclat = clamp(dot(normale, LUMIERE) / LUMIERE.y, 0.45, 1.3); // 1 à plat
                float3 ombre = eclat * lerp(FROIDE, CHAUDE, saturate((eclat - 0.45) / 0.85));
                float cime = smoothstep(0.5 * _Plafond, 0.9 * _Plafond, h);
                float3 mer = lerp(_Rivage.rgb, _Mer.rgb, saturate(-h / _Fond));
                // Hors de la carte, le papier : plein contre la coupe, il prend peu à peu la mer du large en s'en éloignant.
                // La grille dit 1 au-delà de la coupe et 0 en deçà : à mi-chemin, sur la coupe, c'est déjà du papier.
                // L'estompe vaut 1 de part et d'autre de la coupe : un pixel que la grille des lieux, plus fine, donne à la mer
                // contre la coupe y prend aussi le papier, au lieu d'y tirer un pointillé de rivage.
                float estompe = smoothstep(0.0, 1.0, SAMPLE_TEXTURE2D(_Estompe, sampler_Relief, i.uv).r);
                float2 auDela = SAMPLE_TEXTURE2D(_HorsCarte, sampler_Relief, i.uv).rg; float hors = max(saturate(2.0 * auDela.r), estompe);
                mer = lerp(mer, lerp(_Papier.rgb, _Mer.rgb, PAPIER_AU_LARGE * (1.0 - auDela.g)), hors);

                // La teinte du lieu, fondue sur un pixel dans celle d'en face ; un lieu sans teinte rend la mer.
                float3 altitude = TeinteDAltitude(h);
                bool terre = teinte[ici].a > 0.5;
                float3 couleur = terre ? lerp(TeinteDuLieu(teinte[ici], altitude), _Roche.rgb, 0.4 * cime) * ombre : mer;
                if (voisine)
                {
                    // La terre d'en face, estompée comme elle le sera chez elle : contre la coupe, la mer n'en tire pas un liseré.
                    float3 autre = teinte[enFace].a > 0.5 ? lerp(lerp(TeinteDuLieu(teinte[enFace], altitude), _Roche.rgb, 0.4 * cime) * ombre, _Papier.rgb, estompe) : mer;
                    couleur = lerp(autre, couleur, saturate(0.5 + auBord.px));
                }

                // La frontière du pays qui tient le point : la mer et les lieux sans teinte ne lui en font pas.
                float lePays = pays[ici];
                for (k = 0; k < 4; k++) s[k] = frontiere[k] * ((pays[k] == lePays || teinte[k].a < 0.5) ? 1.0 : -1.0);
                Lecture aLaFrontiere = Lire(s, poids, f, dx, dy);
                uint c = (uint)lePays;
                float3 teinteDuPays = LOAD_TEXTURE2D(_TeintesDesPays, int2(c % largeurPalette, c / largeurPalette)).rgb;
                float bande = saturate(1.0 - aLaFrontiere.brute / clamp(LISERE_PX * kmParPixel, LISERE_MIN_KM, LISERE_MAX_KM));
                float surTerre = terre ? 1.0 : 0.0;
                couleur = lerp(couleur, teinteDuPays * ombre, surTerre * (c > 0 ? 1.0 : 0.0) * FORCE_DU_LISERE * bande * _ForceDesPays * _ForceDesLiseres);
                // Le bord entre deux lieux de terre, léger de près, effacé de loin.
                float entreTerres = voisine && teinte[enFace].a > 0.5 ? surTerre : 0.0;
                couleur = lerp(couleur, _EncreDesBords.rgb, entreTerres * BORD_PRES * (1.0 - smoothstep(BORD_PRES_KM, BORD_LOIN_KM, kmParPixel)) * Trait(auBord.px, BORD_PX));
                couleur = lerp(couleur, _EncreDesFrontieres.rgb, surTerre * _EncreDesFrontieres.a * _ForceDesPays * Trait(aLaFrontiere.px, max(FRONTIERE_PX, FRONTIERE_KM / kmParPixel)));
                // Près d'une coupe, la terre, son liseré et ses frontières s'effacent dans le papier d'au-delà : sur la coupe, c'est déjà lui.
                couleur = lerp(couleur, _Papier.rgb, surTerre * estompe);

                // La côte, et au large les lignes d'eau qui la suivent.
                for (k = 0; k < 4; k++) s[k] = cote[k] * (numero[k] != 0 ? 1.0 : -1.0);
                Lecture aLaCote = Lire(s, poids, f, dx, dy);
                float3 auLarge = abs(-aLaCote.brute - EAUX_KM) / aLaCote.pixel;
                // Ni lignes d'eau ni côte contre le papier : la coupe n'est pas un rivage, ni de son côté de mer, ni de son côté de terre estompée.
                float pasDeRivage = 1.0 - hors;
                float eaux = dot(EAUX, saturate(1.2 - auLarge)) * (1.0 - smoothstep(0.6, 1.1, kmParPixel)) * pasDeRivage;
                couleur = lerp(couleur, _EncreDesEaux.rgb, eaux);
                couleur = lerp(couleur, _EncreDesCotes.rgb, _EncreDesCotes.a * pasDeRivage * Trait(abs(aLaCote.px), max(COTE_PX, COTE_KM / kmParPixel)));

                // Le trait de la marque, par-dessus tout : là où s'annule la distance signée au bord de la cellule marquée.
                for (k = 0; k < 4; k++) s[k] = marque[k] * ((numero[k] >= _LieuxMarques.x && numero[k] <= _LieuxMarques.y) ? 1.0 : -1.0);
                Lecture aLaMarque = Lire(s, poids, f, dx, dy);
                float marquee = _LieuxMarques.x > 0.0 ? 1.0 : 0.0;
                couleur = lerp(couleur, _CouleurDeLaMarque.rgb, marquee * Trait(abs(aLaMarque.px), max(MARQUE_PX, MARQUE_KM / kmParPixel)));
                return half4(couleur, 1);
            }
            ENDHLSL
        }
        Pass
        {
            Name "DepthOnly" Tags { "LightMode" = "DepthOnly" }
            Cull Off ZWrite On ColorMask R
            HLSLPROGRAM
            #pragma target 4.5
            #pragma vertex Vert
            #pragma fragment Profondeur
            half Profondeur(V i) : SV_Target { return i.clip.z; }
            ENDHLSL
        }
    }
}
