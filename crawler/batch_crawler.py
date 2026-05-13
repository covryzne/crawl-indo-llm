async def crawl_in_batches(crawler, urls, run_config, batch_size=10):
    results = []

    for start_index in range(0, len(urls), batch_size):
        batch_urls = urls[start_index : start_index + batch_size]
        batch_results = await crawler.arun_many(batch_urls, config=run_config)
        results.extend(batch_results)

    return results
