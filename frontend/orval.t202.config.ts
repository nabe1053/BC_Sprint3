import config from './orval.config'

export default {
  ...config,
  api: { ...config.api, output: { ...config.api.output, clean: false } },
}
