// Marche cuite : phase dans [0,1[, deux lignes voisines en boucle. _VATActif à 0 garde la référence.
Shader "Forge/CivilVAT"
{
    Properties
    {
        [NoScaleOffset] _VAT("Animation cuite", 2D) = "black" {}
        _Phase("Phase de marche", Range(0, 1)) = 0 _ImagesMarche("Images de marche", Float) = 24
        _Coins("Coins", Float) = 0 _VATActif("Animation active", Float) = 1
        _Teinte("Teinte de la tunique", Color) = (1, 1, 1, 1)
    }
    SubShader
    {
        Tags { "RenderType" = "Opaque" "RenderPipeline" = "UniversalPipeline" "Queue" = "Geometry" }
        Pass
        {
            Name "ForwardLit" Tags { "LightMode" = "UniversalForward" }
            HLSLPROGRAM
            #pragma target 4.5
            #pragma vertex Vert
            #pragma fragment Frag
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"
            CBUFFER_START(UnityPerMaterial)
                float _Phase, _ImagesMarche, _Coins, _VATActif; float4 _Teinte;
            CBUFFER_END
            TEXTURE2D(_VAT);
            struct A { float3 p : POSITION; float3 n : NORMAL; float4 c : COLOR; uint id : SV_VertexID; };
            struct V { float4 clip : SV_POSITION; float3 n : TEXCOORD0; float3 alb : TEXCOORD1; };
            void Lire(uint id, uint ligne, out float3 p, out float3 n)
            { uint c = (uint)_Coins; p = LOAD_TEXTURE2D_LOD(_VAT, uint2(id, ligne), 0).xyz; n = LOAD_TEXTURE2D_LOD(_VAT, uint2(id + c, ligne), 0).xyz; }
            V Vert(A a)
            {
                float3 p = a.p, n = a.n;
                if (_VATActif >= 0.5)
                {
                    float f = frac(_Phase) * _ImagesMarche, t; uint i = (uint)floor(f), j = (i + 1) % (uint)max(_ImagesMarche, 1); t = frac(f);
                    float3 p0, n0, p1, n1; Lire(a.id, i, p0, n0); Lire(a.id, j, p1, n1); p = lerp(p0, p1, t); n = normalize(lerp(n0, n1, t));
                }
                V o; o.clip = TransformObjectToHClip(p); o.n = TransformObjectToWorldNormal(n);
                o.alb = a.c.rgb * lerp(float3(1, 1, 1), _Teinte.rgb, a.c.a); return o;
            }
            half4 Frag(V i) : SV_Target { float3 n = normalize(i.n); Light s = GetMainLight(); return half4(i.alb * (s.color * saturate(dot(n, s.direction)) + max(SampleSH(n), 0.22)), 1); }
            ENDHLSL
        }
    }
}
