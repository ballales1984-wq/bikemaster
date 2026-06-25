import { mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'

const apiGet = vi.hoisted(() => vi.fn())
const apiPost = vi.hoisted(() => vi.fn())
vi.mock('../utils/api.ts', () => ({ apiGet, apiPost }))

import KnowledgePanel from './KnowledgePanel.vue'

function flush() {
  return new Promise(resolve => setTimeout(resolve, 0))
}

const mockSearchResult = {
  results: [
    { topic: 'Training', content: 'Improve your aerobic capacity' },
    { topic: 'FTP', content: 'Functional Threshold Power guide' },
  ],
}

const mockTopics = ['Training', 'Nutrition', 'Recovery', 'FTP', 'Endurance']

describe('KnowledgePanel', () => {
  afterEach(() => {
    vi.clearAllMocks()
  })

  it('loads with empty search input', async () => {
    const wrapper = mount(KnowledgePanel)
    await flush()

    const input = wrapper.find('.search-input')
    expect(input.exists()).toBe(true)
    expect(input.element.value).toBe('')
  })

  it('displays Knowledge Base title', async () => {
    const wrapper = mount(KnowledgePanel)
    await flush()

    expect(wrapper.find('h2').text()).toContain('Knowledge Base')
  })

  it('searches on button click', async () => {
    apiGet.mockResolvedValueOnce(mockSearchResult)

    const wrapper = mount(KnowledgePanel)
    await flush()

    const input = wrapper.find('.search-input')
    await input.setValue('cycling')
    await wrapper.find('.search-btn').trigger('click')
    await flush()

    expect(apiGet).toHaveBeenCalledWith('/api/v1/knowledge/search', { q: 'cycling' })
  })

  it('shows results after search', async () => {
    apiGet.mockResolvedValueOnce(mockSearchResult)

    const wrapper = mount(KnowledgePanel)
    await flush()

    const input = wrapper.find('.search-input')
    await input.setValue('VO2 Max')
    await wrapper.find('.search-btn').trigger('click')
    await flush()

    expect(wrapper.text()).toContain('Training')
  })

  it('shows search error gracefully', async () => {
    apiGet.mockRejectedValueOnce(new Error('Search failed'))

    const wrapper = mount(KnowledgePanel)
    await flush()

    const input = wrapper.find('.search-input')
    await input.setValue('test')
    await wrapper.find('.search-btn').trigger('click')
    await flush()

    expect(wrapper.text()).toContain('Nessun risultato')
  })

  it('loads topics on mount', async () => {
    apiGet.mockResolvedValueOnce(mockTopics)
    apiGet.mockResolvedValueOnce({ topics: [], total_documents: 0 })

    const wrapper = mount(KnowledgePanel)
    await flush()

    expect(apiGet).toHaveBeenCalledWith('/api/v1/knowledge')
  })

  it('searches topic on pill click', async () => {
    apiGet.mockResolvedValueOnce(mockTopics)
    apiGet.mockResolvedValueOnce({ topics: [], total_documents: 0 })
    apiGet.mockResolvedValueOnce(mockSearchResult)

    const wrapper = mount(KnowledgePanel)
    await flush()

    const topicPills = wrapper.findAll('.topic-pill')
    if (topicPills.length > 0) {
      await topicPills[0].trigger('click')
      await flush()
    }
  })

  it('has clear search button when query exists', async () => {
    const wrapper = mount(KnowledgePanel)
    await flush()

    const input = wrapper.find('.search-input')
    await input.setValue('test query')

    expect(wrapper.find('.clear-btn').exists()).toBe(true)
  })
})