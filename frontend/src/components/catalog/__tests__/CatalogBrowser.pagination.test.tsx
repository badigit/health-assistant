import React, { useState } from 'react';
import { describe, expect, it, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { CatalogBrowser } from '../CatalogBrowser';

vi.mock('react-i18next', () => ({ useTranslation: () => ({
  i18n:{language:'en'},
  t:(key:string, fallback?:string | {defaultValue?:string}) =>
    typeof fallback==='string' ? fallback : fallback?.defaultValue ?? key,
}) }));
vi.mock('../../../store/slices/authSlice', () => ({ useAuthStore:(selector:(state:unknown)=>unknown) => selector({user:null}) }));

const items = Array.from({length:75},(_,index)=>({id:String(index),name:`Metric ${String(index).padStart(2,'0')}`,
  updated_at:new Date(Date.UTC(2026,0,index+1)).toISOString()}));

function Browser({selected}:{selected?:string}) {
  const [limit,setLimit] = useState(50);
  return <CatalogBrowser items={items} total={75} visibleLimit={limit} loading={false}
    viewMode="list" domainRoute={()=>null} onSelectItem={()=>{}} selectedItemId={selected}
    hasMore={limit<items.length} onLoadMore={()=>setLimit(limit+50)} />;
}

describe('catalog display pagination',()=>{
  it('renders subsequent matches once without changing the filtered total',()=>{
    render(<Browser />);
    expect(screen.getByText('50 of 75')).toBeInTheDocument();
    expect(screen.queryByText('Metric 74')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button',{name:'Load more'}));
    expect(screen.getByText('75 total')).toBeInTheDocument();
    expect(screen.getAllByText('Metric 74')).toHaveLength(1);
    expect(screen.getAllByText('Metric 00')).toHaveLength(1);
    expect(screen.queryByRole('button',{name:'Load more'})).not.toBeInTheDocument();
  });

  it('sorts the full collection before taking the visible page',()=>{
    render(<Browser />);
    fireEvent.click(screen.getByRole('button',{name:'Updated'}));
    expect(screen.getByText('Metric 74')).toBeInTheDocument();
    expect(screen.queryByText('Metric 00')).not.toBeInTheDocument();
  });

  it('reveals a selected later item without adding a duplicate to the collection',()=>{
    render(<Browser selected="74" />);
    expect(screen.getByText('75 total')).toBeInTheDocument();
    expect(screen.getAllByText('Metric 74')).toHaveLength(1);
    expect(screen.queryByRole('button',{name:'Load more'})).not.toBeInTheDocument();
  });
});
