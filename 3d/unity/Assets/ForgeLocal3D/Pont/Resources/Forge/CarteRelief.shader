// Le terrain de la carte, d'un seul tenant. La teinte de chaque cellule se lit dans la palette par le numéro de son
// texel. Les traits ne viennent pas de la grille mais des distances mesurées aux côtés servis (`_Bords`, `_Frontieres`) :
// entre quatre texels voisins, la distance signée à un bord se lit comme une pente, et le trait se pose là où elle
// s'annule, large d'un nombre de pixels choisi. Un bord de cellule, une côte, une frontière restent donc des traits
// nets à tout zoom, jamais un escalier. Du sol vers le dessus : la teinte, le liseré du pays le long de sa frontière,
// le bord des cellules, la frontière, les lignes d'eau au large du rivage, la côte.
// Le relief ombre la terre d'une lumière fixe du nord-ouest et pâlit les cimes ; la mer s'éclaircit vers le rivage et
// rend au large la couleur exacte de `_Mer`, celle du fond de la caméra. Rien n'est éclairé par la scène : la carte
// est mate. La lumière est un peu chaude sur les versants éclairés, un peu froide dans l'ombre. De près, quand un pixel
// couvre moins d'un km, un grain fin anime le relief, plus fort sur les pentes : sans lui le relief, levé tous les
// deux km, se lit comme un flou. Autour de la carte, un cadre : un filet épais doublé d'un filet fin, et au-delà la
// table, de la couleur du fond de la caméra. Le terrain se dessine avant tout le reste de la carte : les noms des pays s'impriment sur lui, puis
// viennent les objets posés dessus.
Shader "Forge/CarteRelief"
{
    Properties
    {
        [NoScaleOffset] _Cellules("Cellules", 2D) = "black" {}
        [NoScaleOffset] _Palette("Palette", 2D) = "black" {}
        [NoScaleOffset] _Relief("Relief", 2D) = "black" {}
        [NoScaleOffset] _Bords("Distances au bord de la cellule et à la côte", 2D) = "white" {}
        [NoScaleOffset] _Frontieres("Distances à la frontière", 2D) = "white" {}
        [NoScaleOffset] _Pays("Pays de chaque cellule", 2D) = "black" {}
        [NoScaleOffset] _TeintesDesPays("Teinte de chaque pays", 2D) = "black" {}
        _Mer("Mer au large", Color) = (0.08, 0.16, 0.3, 1)
        _Rivage("Mer au rivage", Color) = (0.2, 0.3, 0.42, 1)
        _Roche("Cimes", Color) = (0.85, 0.83, 0.78, 1)
        _EncreDesCotes("Encre des côtes", Color) = (0.1, 0.08, 0.06, 1)
        _EncreDesBords("Encre des bords de cellules", Color) = (0.1, 0.08, 0.06, 1)
        _EncreDesFrontieres("Encre des frontières", Color) = (0.1, 0.08, 0.06, 1)
        _EncreDesEaux("Encre des lignes d'eau", Color) = (0.5, 0.6, 0.7, 1)
        _Pas("Pas des cellules, en km", Float) = 1
        _PorteeDesBords("Portée des distances aux bords, en km", Float) = 12
        _PorteeDesFrontieres("Portée des distances aux frontières, en km", Float) = 16
        _PasDuRelief("Pas du relief, en km", Float) = 2
        _Fond("Fond de la mer, en km", Float) = 6
        _Plafond("Plus haute cime, en km", Float) = 40
        _Vigueur("Vigueur de l'ombre", Float) = 1.6
        _Grain("Force du grain de près", Float) = 1
        _Table("Table autour de la carte", Color) = (0.08, 0.16, 0.3, 1)
        _Filet("Filet du cadre", Color) = (0.1, 0.08, 0.06, 0)
        _Cadre("Cadre de la carte, en km depuis le coin du terrain : ouest, sud, est, nord", Vector) = (-1000000, -1000000, 1000000, 1000000)
    }
    SubShader
    {
        Tags { "RenderType" = "Opaque" "RenderPipeline" = "UniversalPipeline" "Queue" = "Geometry-10" }
        HLSLINCLUDE
        #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
        CBUFFER_START(UnityPerMaterial)
            float4 _Cellules_TexelSize, _Palette_TexelSize, _Relief_TexelSize;
            float4 _Mer, _Rivage, _Roche, _EncreDesCotes, _EncreDesBords, _EncreDesFrontieres, _EncreDesEaux;
            float4 _Table, _Filet, _Cadre;
            float _Pas, _PorteeDesBords, _PorteeDesFrontieres, _PasDuRelief, _Fond, _Plafond, _Vigueur, _Grain;
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
            TEXTURE2D(_Cellules); TEXTURE2D(_Palette); TEXTURE2D(_Relief); SAMPLER(sampler_Relief);
            TEXTURE2D(_Bords); TEXTURE2D(_Frontieres); TEXTURE2D(_Pays); TEXTURE2D(_TeintesDesPays);
            static const float3 LUMIERE = float3(-0.5145, 0.686, 0.5145); // du nord-ouest, à mi-hauteur
            // En km : sous ce plancher, un texel posé sur un bord ne dit plus de quel côté il est.
            static const float PLANCHER = 0.02;
            // Le liseré d'un pays s'efface sur dix-huit pixels, entre deux km et demi et quatorze ; la frontière et la
            // côte ont une demi-largeur en km, et jamais moins que leur demi-largeur en pixels.
            static const float LISERE_PX = 18.0, LISERE_MIN_KM = 2.5, LISERE_MAX_KM = 14.0, FORCE_DU_LISERE = 0.8;
            static const float FRONTIERE_KM = 0.3, FRONTIERE_PX = 1.1, COTE_KM = 0.18, COTE_PX = 0.7, BORD_PX = 0.5;
            // Les lignes d'eau, en km du rivage, et ce que chacune couvre de la mer ; elles s'effacent quand un pixel
            // dépasse le km, où elles se toucheraient.
            static const float3 EAUX_KM = float3(2.5, 5.5, 9.0), EAUX = float3(0.34, 0.22, 0.12);

            // Le cadre : son filet épais a cette demi-largeur, en km et jamais moins qu'en pixels ; le filet fin est en dedans.
            static const float FILET_KM = 7.0, FILET_PX = 2.0, FILET_FIN_PX = 0.8;
            // La lumière des versants éclairés et celle de l'ombre.
            static const float3 CHAUDE = float3(1.05, 1.0, 0.93), FROIDE = float3(0.9, 0.95, 1.05);

            float Altitude(float2 uv) { return SAMPLE_TEXTURE2D(_Relief, sampler_Relief, uv).r; }

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
                float2 p = i.uv * _Cellules_TexelSize.zw - 0.5, base = floor(p), f = p - base;
                int2 dernier = int2(_Cellules_TexelSize.zw) - 1; uint largeurPalette = (uint)_Palette_TexelSize.z;
                float poids[4] = { (1 - f.x) * (1 - f.y), f.x * (1 - f.y), (1 - f.x) * f.y, f.x * f.y };
                float numero[4], pays[4], bord[4], cote[4], frontiere[4], s[4], vote[4]; float4 teinte[4];
                int k, a;
                for (k = 0; k < 4; k++)
                {
                    int2 q = clamp(int2(base) + int2(k & 1, k >> 1), int2(0, 0), dernier);
                    numero[k] = round(LOAD_TEXTURE2D(_Cellules, q).r * 65535.0);
                    uint n = (uint)numero[k]; int2 rangee = int2(n % largeurPalette, n / largeurPalette);
                    teinte[k] = LOAD_TEXTURE2D(_Palette, rangee);
                    pays[k] = round(LOAD_TEXTURE2D(_Pays, rangee).r * 65535.0);
                    float2 b = LOAD_TEXTURE2D(_Bords, q).rg; float v = LOAD_TEXTURE2D(_Frontieres, q).r;
                    bord[k] = max(_PorteeDesBords * b.r * b.r, PLANCHER); cote[k] = _PorteeDesBords * b.g * b.g;
                    frontiere[k] = _PorteeDesFrontieres * v * v;
                }
                // Le point, en km de la carte, et ce qu'un pixel de l'écran en couvre.
                float2 km = i.uv * _Cellules_TexelSize.zw * _Pas, dx = ddx(km), dy = ddy(km);
                float kmParPixel = max(max(length(dx), length(dy)), 1e-6);

                // La cellule du point : celle dont la distance signée à son bord, lue entre les quatre texels, est la
                // plus grande ; la suivante est celle d'en face, et quand les quatre texels sont de la même cellule,
                // elle n'a pas de voisine ici.
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

                // La teinte de la cellule, fondue sur un pixel dans celle d'en face ; une cellule sans teinte rend la mer.
                bool terre = teinte[ici].a > 0.5;
                float3 couleur = terre ? lerp(teinte[ici].rgb, _Roche.rgb, 0.4 * cime) * ombre : mer;
                if (voisine)
                {
                    float3 autre = teinte[enFace].a > 0.5 ? lerp(teinte[enFace].rgb, _Roche.rgb, 0.4 * cime) * ombre : mer;
                    couleur = lerp(autre, couleur, saturate(0.5 + auBord.px));
                }

                // La frontière du pays qui tient le point : la mer et les cellules sans teinte ne lui en font pas.
                float lePays = pays[ici];
                for (k = 0; k < 4; k++) s[k] = frontiere[k] * ((pays[k] == lePays || teinte[k].a < 0.5) ? 1.0 : -1.0);
                Lecture aLaFrontiere = Lire(s, poids, f, dx, dy);
                uint c = (uint)lePays;
                float3 teinteDuPays = LOAD_TEXTURE2D(_TeintesDesPays, int2(c % largeurPalette, c / largeurPalette)).rgb;
                float bande = saturate(1.0 - aLaFrontiere.brute / clamp(LISERE_PX * kmParPixel, LISERE_MIN_KM, LISERE_MAX_KM));
                float surTerre = terre ? 1.0 : 0.0;
                couleur = lerp(couleur, teinteDuPays * ombre, surTerre * (c > 0 ? 1.0 : 0.0) * FORCE_DU_LISERE * bande);
                // Le bord entre deux cellules de terre, plus discret quand la carte s'éloigne.
                float entreTerres = voisine && teinte[enFace].a > 0.5 ? surTerre : 0.0;
                couleur = lerp(couleur, _EncreDesBords.rgb, entreTerres * lerp(0.5, 0.22, saturate((kmParPixel - 0.3) / 1.5)) * Trait(auBord.px, BORD_PX));
                couleur = lerp(couleur, _EncreDesFrontieres.rgb, surTerre * _EncreDesFrontieres.a * Trait(aLaFrontiere.px, max(FRONTIERE_PX, FRONTIERE_KM / kmParPixel)));

                // La côte, et au large les lignes d'eau qui la suivent.
                for (k = 0; k < 4; k++) s[k] = cote[k] * (numero[k] != 0 ? 1.0 : -1.0);
                Lecture aLaCote = Lire(s, poids, f, dx, dy);
                float3 auLarge = abs(-aLaCote.brute - EAUX_KM) / aLaCote.pixel;
                float eaux = dot(EAUX, saturate(1.2 - auLarge)) * (1.0 - smoothstep(0.6, 1.1, kmParPixel));
                couleur = lerp(couleur, _EncreDesEaux.rgb, eaux);
                couleur = lerp(couleur, _EncreDesCotes.rgb, _EncreDesCotes.a * Trait(abs(aLaCote.px), max(COTE_PX, COTE_KM / kmParPixel)));

                // Le bord de la carte : au-delà du cadre, la table ; sur lui, le filet épais ; un peu en dedans, le filet fin.
                float2 auDela = max(_Cadre.xy - km, km - _Cadre.zw); float dehors = max(auDela.x, auDela.y) / kmParPixel; // en pixels, négatif en dedans
                float epais = max(FILET_PX, FILET_KM / kmParPixel);
                couleur = lerp(couleur, _Table.rgb, saturate(dehors + 0.5));
                couleur = lerp(couleur, _Filet.rgb, _Filet.a * Trait(abs(dehors + epais), epais));
                couleur = lerp(couleur, _Filet.rgb, _Filet.a * Trait(abs(dehors + 3.2 * epais), FILET_FIN_PX));
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
