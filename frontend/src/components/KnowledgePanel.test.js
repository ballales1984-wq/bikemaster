import { mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

const apiGet = vi.hoisted(() => vi.fn())
vi.mock('../utils/api.ts', () => ({ apiGet }))

import KnowledgePanel from './KnowledgePanel.vue'

function flush() {
  return new Promise(resolve => setTimeout(resolve, 0))
}

const mockSearchResult = {
  results: [
    { title: 'VO2 Max Training', snippet: 'Improve your aerobic capacity' },
    { title: 'FTP Testing', snippet: 'Functional Threshold Power guide' },
  ],
}

const mockSecondSearch = {
  results: [
    { title: 'Hill Climbing', snippet: 'Techniques for steep ascents' },
    { title: 'Cadence Drills', snippet: 'Improve pedal efficiency' },
  ],
}

const mockTopics = {
  topics: [
    { id: 1, title: 'Training Plans', category: 'Endurance' },
    { id: 2, title: 'Nutrition', category: 'Diet' },
    { id: 3, title: 'Recovery', category: 'Health' },
  ],
}

describe('KnowledgePanel', () => {
  afterEach(() => {
    vi.clearAllMocks()
  })

  it('loads with empty form', async () => {
    const wrapper = mount(KnowledgePanel)

    expect(wrapper.find('#kb-query').exists()).toBe(true)
    expect(wrapper.find('#kb-query').element.value).toBe('')
  })

  it('search button triggers search', async () => {
    apiGet.mockResolvedValueOnce(mockSearchResult)

    const wrapper = mount(KnowledgePanel)
    await flush()

    await wrapper.find('#kb-query').setValue('VO2 Max')
    await wrapper.find('button.btn-primary').trigger('click')
    await flush()

    expect(apiGet).toHaveBeenCalledWith('/api/v1/knowledge/search', { query: 'VO2 Max' })
    expect(wrapper.find('.result-box').text()).toContain('VO2 Max Training')
  })

  it('list topics button triggers topics fetch', async () => {
    apiGet.mockResolvedValueOnce(mockTopics)

    const wrapper = mount(KnowledgePanel)
    await flush()

    await wrapper.find('button.btn-secondary').trigger('click')
    await flush()

    expect(apiGet).toHaveBeenCalledWith('/api/v1/knowledge')
    expect(wrapper.find('.result-box').text()).toContain('Training Plans')
  })

  it('shows search error gracefully', async () => {
    apiGet.mockRejectedValueOnce(new Error('Search failed'))

    const wrapper = mount(KnowledgePanel)
    await flush()

    await wrapper.find('#kb-query').setValue('test')
    await wrapper.find('button.btn-primary').trigger('click')
    await flush()

    expect(wrapper.find('.result-box').text()).toContain('Error')
  })

  it('shows topics error gracefully', async () => {
    apiGet.mockRejectedValueOnce(new Error('Topics failed'))

    const wrapper = mount(KnowledgePanel)
    await flush()

    await wrapper.find('button.btn-secondary').trigger('click')
    await flush()

    expect(wrapper.find('.result-box').text()).toContain('Error')
  })

  it('updates query input on typing', async () => {
    const wrapper = mount(KnowledgePanel)

    await wrapper.find('#kb-query').setValue('endurance training')
    await wrapper.vm.$nextTick()

    expect(wrapper.find('#kb-query').element.value).toBe('endurance training')
  })

  it('displays Knowledge Base title', async () => {
    const wrapper = mount(KnowledgePanel)

    expect(wrapper.find('h2').text()).toContain('Knowledge Base')
  })

  it('has search and list buttons', async () => {
    const wrapper = mount(KnowledgePanel)

    expect(wrapper.text()).toContain('Search')
    expect(wrapper.text()).toContain('List Topics')
  })

  it('renders form group', async () => {
    const wrapper = mount(KnowledgePanel)

    expect(wrapper.find('.form-grid').exists()).toBe(true)
    expect(wrapper.find('.form-group').exists()).toBe(true)
  })

  it('shows result box after search', async () => {
    apiGet.mockResolvedValueOnce(mockSearchResult)

    const wrapper = mount(KnowledgePanel)
    await flush()

    await wrapper.find('#kb-query').setValue('cycling')
    await wrapper.find('button.btn-primary').trigger('click')
    await flush()

    expect(wrapper.find('.result-box').exists()).toBe(true)
  })

  it('search with empty query still makes API call', async () => {
    apiGet.mockResolvedValueOnce(mockSearchResult)

    const wrapper = mount(KnowledgePanel)
    await flush()

    await wrapper.find('button.btn-primary').trigger('click')
    await flush()

    expect(apiGet).toHaveBeenCalledWith('/api/v1/knowledge/search', { query: '' })
  })

  it('list topics shows category', async () => {
    apiGet.mockResolvedValueOnce(mockTopics)

    const wrapper = mount(KnowledgePanel)
    await flush()

    await wrapper.find('button.btn-secondary').trigger('click')
    await flush()

    expect(wrapper.find('.result-box').text()).toContain('Nutrition')
  })

  it('multiple searches update result sequentially', async () => {
    let searchCount = 0
    apiGet.mockImplementation(() => {
      searchCount += 1
      if (searchCount === 1) return Promise.resolve(mockSearchResult)
      return Promise.resolve(mockSecondSearch)
    })

    const wrapper = mount(KnowledgePanel)
    await flush()

    await wrapper.find('#kb-query').setValue('power')
    await wrapper.find('button.btn-primary').trigger('click')
    await flush()

    expect(wrapper.find('.result-box').text()).toContain('VO2 Max Training')

    await wrapper.find('#kb-query').setValue('hills')
    await wrapper.find('button.btn-primary').trigger('click')
    await flush()

    expect(wrapper.find('.result-box').text()).toContain('Hill Climbing')
  })

  it('has input label for search topic', async () => {
    const wrapper = mount(KnowledgePanel)

    expect(wrapper.text()).toContain('Search topic')
  })

  it('list topics shows all categories', async () => {
    apiGet.mockResolvedValueOnce(mockTopics)

    const wrapper = mount(KnowledgePanel)
    await flush()

    await wrapper.find('button.btn-secondary').trigger('click')
    await flush()

    expect(wrapper.find('.result-box').text()).toContain('Diet')
    expect(wrapper.find('.result-box').text()).toContain('Health')
  })

  it('switches from topics back to search', async () => {
    apiGet.mockResolvedValueOnce(mockTopics)
    apiGet.mockResolvedValueOnce(mockSearchResult)

    const wrapper = mount(KnowledgePanel)
    await flush()

    await wrapper.find('button.btn-secondary').trigger('click')
    await flush()

    expect(wrapper.find('.result-box').text()).toContain('Training Plans')

    await wrapper.find('#kb-query').setValue('VO2 Max')
    await wrapper.find('button.btn-primary').trigger('click')
    await flush()

    expect(wrapper.find('.result-box').text()).toContain('VO2 Max Training')
  })

  it('renders btn-primary and btn-secondary', async () => {
    const wrapper = mount(KnowledgePanel)

    expect(wrapper.find('button.btn-primary').exists()).toBe(true)
    expect(wrapper.find('button.btn-secondary').exists()).toBe(true)
  })

  it('clears query on mount', async () => {
    const wrapper = mount(KnowledgePanel)

    expect(wrapper.find('#kb-query').element.value).toBe('')
  })

  it('search result box shows JSON formatted data', async () => {
    apiGet.mockResolvedValueOnce({ results: [{ title: 'Test Topic' }] })

    const wrapper = mount(KnowledgePanel)
    await flush()

    await wrapper.find('button.btn-secondary').trigger('click')
    await flush()

    expect(wrapper.find('.result-box').text()).not.toBe('')
    expect(wrapper.find('.result-box').text()).toContain('Test Topic')
  })
})
