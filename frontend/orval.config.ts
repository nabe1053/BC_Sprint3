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
      mutator: {
        path: './src/shared/api/mutator.ts',
        name: 'customInstance',
      },
      clean: true,
      prettier: true,
    },
  },
}

export default config
