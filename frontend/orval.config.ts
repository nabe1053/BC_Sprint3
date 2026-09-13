const config = {
  api: {
    input: {
      target: '../backend/openapi.json',
    },
    output: {
      // タグごとにファイル分割: generated/{tag}.ts + 型は generated/model/
      // 例: import { useGetApplications } from '@/shared/api/generated/applications'
      mode: 'tags',
      target: './src/shared/api/generated',
      schemas: './src/shared/api/generated/model',
      // TanStack Query のフックを生成（features/*/api.ts が wrap して使う）
      client: 'react-query',
      httpClient: 'fetch',
      clean: true,
      formatter: 'prettier',
      override: {
        operations: {
          create_export_api_v1_ui_versions__versionId__exports_post: {
            mutator: {
              path: './src/shared/api/mutator.ts',
              name: 'binaryInstance',
            },
          },
        },
        // mutator は output.override 配下でないと生成コードに反映されない。
        // 直下に書くと orval は黙って無視し、生成物が素の fetch（baseURL 無し・
        // 非2xx を投げない）になる。T-103 で発覚（memory LN-010）。
        mutator: {
          path: './src/shared/api/mutator.ts',
          name: 'customInstance',
        },
      },
    },
  },
}

export default config
