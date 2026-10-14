import React, { useState, useEffect } from "react";
import { Search, Filter, ShoppingBag, Sparkles, AlertCircle, ChevronLeft, ChevronRight, ArrowUpDown, X } from "lucide-react";
import { fetchProducts } from "../services/api";
import { fetchDemoProducts, isDemoSession } from "../services/demoService";
import type { ProductItem } from "../types";
import { HierarchicalCategoryDropdown } from "./HierarchicalCategoryDropdown";
import { ProductCard } from "./ProductCard";

interface ProductBrowseViewProps {
  onAskInChat: (query: string) => void;
  onReportProduct: (productId: string) => void;
  isDemo?: boolean;
}

export const ProductBrowseView: React.FC<ProductBrowseViewProps> = ({
  onAskInChat,
  onReportProduct,
  isDemo: propIsDemo,
}) => {
  const isDemo = Boolean(propIsDemo ?? isDemoSession());
  const [products, setProducts] = useState<ProductItem[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>("");
  const [search, setSearch] = useState<string>("");
  const [appliedSearch, setAppliedSearch] = useState<string>("");
  const [minPrice, setMinPrice] = useState<string>("");
  const [maxPrice, setMaxPrice] = useState<string>("");
  const [appliedMinPrice, setAppliedMinPrice] = useState<string>("");
  const [appliedMaxPrice, setAppliedMaxPrice] = useState<string>("");
  const [inStockOnly, setInStockOnly] = useState<boolean>(false);
  const [sortBy, setSortBy] = useState<string>("title_asc");
  const [page, setPage] = useState<number>(1);
  const [pageSize] = useState<number>(24);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [totalCount, setTotalCount] = useState<number>(0);

  useEffect(() => {
    loadProducts(page);
  }, [selectedCategory, inStockOnly, sortBy, appliedSearch, appliedMinPrice, appliedMaxPrice, page, isDemo]);

  const loadProducts = async (targetPage: number = page) => {
    setIsLoading(true);
    const offset = (targetPage - 1) * pageSize;
    try {
      const resp = isDemo
        ? await fetchDemoProducts({
            category: selectedCategory || undefined,
            min_price: appliedMinPrice ? parseFloat(appliedMinPrice) : undefined,
            max_price: appliedMaxPrice ? parseFloat(appliedMaxPrice) : undefined,
            in_stock_only: inStockOnly,
            search: appliedSearch.trim() || undefined,
            sort_by: sortBy,
            limit: pageSize,
            offset,
          })
        : await fetchProducts({
            category: selectedCategory || undefined,
            min_price: appliedMinPrice ? parseFloat(appliedMinPrice) : undefined,
            max_price: appliedMaxPrice ? parseFloat(appliedMaxPrice) : undefined,
            in_stock_only: inStockOnly,
            search: appliedSearch.trim() || undefined,
            sort_by: sortBy,
            limit: pageSize,
            offset,
          });
      setProducts(resp.products);
      setCategories(resp.categories);
      setTotalCount(resp.total);
    } catch (err) {
      console.error("Failed to load products:", err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    setAppliedSearch(search);
  };

  const handlePriceApply = () => {
    setPage(1);
    setAppliedMinPrice(minPrice);
    setAppliedMaxPrice(maxPrice);
  };

  const handleCategorySelect = (cat: string) => {
    setPage(1);
    setSelectedCategory(cat);
  };

  const handleResetFilters = () => {
    setSelectedCategory("");
    setSearch("");
    setAppliedSearch("");
    setMinPrice("");
    setMaxPrice("");
    setAppliedMinPrice("");
    setAppliedMaxPrice("");
    setInStockOnly(false);
    setSortBy("title_asc");
    setPage(1);
  };

  const totalPages = Math.max(1, Math.ceil(totalCount / pageSize));
  const hasActiveFilters = Boolean(
    selectedCategory ||
    appliedSearch ||
    appliedMinPrice ||
    appliedMaxPrice ||
    inStockOnly ||
    sortBy !== "title_asc"
  );

  return (
    <div className="space-y-6 animate-fade-in max-w-7xl mx-auto px-4 sm:px-6 py-4">
      {/* Search and Filters Header */}
      <div className="bg-white rounded-2xl p-5 border border-slate-200 shadow-xs space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2">
              <h2 className="text-xl font-bold text-slate-900 tracking-tight flex items-center space-x-2">
                <ShoppingBag className="h-5 w-5 text-indigo-600" />
                <span>{isDemo ? "Predefined Demo Catalog" : "Browse Active Catalogue"}</span>
              </h2>
              {isDemo && (
                <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-[10px] font-extrabold uppercase bg-amber-100 text-amber-900 border border-amber-300">
                  <Sparkles className="h-3 w-3 text-amber-600" />
                  <span>Isolated Demo Dataset</span>
                </span>
              )}
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              {isDemo
                ? "Displaying the predefined sample catalog (16 sample items). Real store owner records are strictly separated."
                : "Every product and attribute here is verified from the store owner's active database catalogue."}
            </p>
          </div>

          <form onSubmit={handleSearchSubmit} className="flex items-center space-x-2 w-full md:w-80">
            <div className="relative flex-1">
              <Search className="h-4 w-4 text-slate-400 absolute left-3 top-2.5" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search title, brand, or SKU..."
                className="w-full pl-9 pr-8 py-2 text-xs rounded-xl border border-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white"
              />
              {search && (
                <button
                  type="button"
                  onClick={() => {
                    setSearch("");
                    setAppliedSearch("");
                    setPage(1);
                  }}
                  className="absolute right-2.5 top-2.5 text-slate-400 hover:text-slate-600"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              )}
            </div>
            <button
              type="submit"
              className="px-3.5 py-2 rounded-xl bg-indigo-600 text-white font-semibold text-xs hover:bg-indigo-700 transition-colors cursor-pointer shrink-0"
            >
              Search
            </button>
          </form>
        </div>

        {/* Filters bar */}
        <div className="flex flex-wrap items-center gap-3 pt-3 border-t border-slate-100 text-xs">
          <div className="flex items-center space-x-1.5 text-slate-500 font-semibold mr-1">
            <Filter className="h-3.5 w-3.5" />
            <span>Filters:</span>
          </div>

          {/* Hierarchical Category Selector */}
          <HierarchicalCategoryDropdown
            categories={categories}
            selectedCategory={selectedCategory}
            onSelectCategory={handleCategorySelect}
            placeholder="Browse All Categories"
          />

          {/* Active Category Filter Badge */}
          {selectedCategory && (
            <div className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-indigo-50 border border-indigo-200 text-indigo-700 font-semibold text-xs animate-fade-in shadow-2xs">
              <span className="text-slate-500 font-normal">Active:</span>
              <span className="font-bold truncate max-w-xs">
                {selectedCategory.replace(/\s*>>\s*/g, " • ").replace(/\s*>\s*/g, " • ")}
              </span>
              <button
                type="button"
                onClick={() => handleCategorySelect("")}
                className="ml-1 p-0.5 rounded-full hover:bg-indigo-200 text-indigo-500 hover:text-indigo-800 cursor-pointer transition-colors"
                title="Clear category filter"
                aria-label="Clear category filter"
              >
                <X className="h-3 w-3" />
              </button>
            </div>
          )}

          {/* Price Range Filters */}
          <div className="flex items-center space-x-1.5">
            <span className="text-slate-500 font-medium">Price:</span>
            <input
              type="number"
              value={minPrice}
              onChange={(e) => setMinPrice(e.target.value)}
              placeholder="Min ₹"
              className="w-20 px-2 py-1 text-xs rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
            <span className="text-slate-400">-</span>
            <input
              type="number"
              value={maxPrice}
              onChange={(e) => setMaxPrice(e.target.value)}
              placeholder="Max ₹"
              className="w-20 px-2 py-1 text-xs rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
            <button
              type="button"
              onClick={handlePriceApply}
              className="px-2.5 py-1 bg-slate-100 hover:bg-slate-200 rounded-lg font-semibold text-slate-700 cursor-pointer transition-colors"
            >
              Apply
            </button>
          </div>

          {/* In Stock toggle */}
          <label className="flex items-center space-x-1.5 font-medium text-slate-700 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={inStockOnly}
              onChange={(e) => {
                setInStockOnly(e.target.checked);
                setPage(1);
              }}
              className="rounded text-indigo-600 focus:ring-indigo-500 h-3.5 w-3.5"
            />
            <span>In Stock Only</span>
          </label>

          {/* Sorting Control */}
          <div className="flex items-center space-x-1.5 ml-auto">
            <ArrowUpDown className="h-3.5 w-3.5 text-slate-400" />
            <span className="text-slate-500 font-medium">Sort:</span>
            <select
              value={sortBy}
              onChange={(e) => {
                setSortBy(e.target.value);
                setPage(1);
              }}
              className="px-2.5 py-1 text-xs rounded-lg border border-slate-300 bg-white font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="title_asc">Title (A-Z)</option>
              <option value="title_desc">Title (Z-A)</option>
              <option value="price_asc">Price: Low to High</option>
              <option value="price_desc">Price: High to Low</option>
              <option value="rating_desc">Top Rated</option>
            </select>
          </div>

          {/* Reset All Filters button */}
          {hasActiveFilters && (
            <button
              type="button"
              onClick={handleResetFilters}
              className="px-2.5 py-1 text-xs text-rose-600 hover:text-rose-800 hover:bg-rose-50 rounded-lg font-semibold cursor-pointer transition-colors"
            >
              Clear All
            </button>
          )}
        </div>
      </div>

      {/* Product Grid */}
      {isLoading ? (
        <div className="py-20 text-center text-slate-400 text-xs">
          Loading {isDemo ? "predefined demo showcase" : "verified catalogue"} products...
        </div>
      ) : products.length === 0 ? (
        <div className="bg-white rounded-2xl p-12 text-center border border-slate-200 space-y-3">
          <div className="h-12 w-12 rounded-full bg-slate-100 text-slate-400 mx-auto flex items-center justify-center">
            <AlertCircle className="h-6 w-6" />
          </div>
          <h3 className="text-base font-bold text-slate-800">No Products Matched Your Criteria</h3>
          <p className="text-xs text-slate-500 max-w-sm mx-auto">
            TruthCart AI never invents or fabricates products to fill the screen. Try relaxing your filters or resetting category and budget parameters.
          </p>
          {hasActiveFilters && (
            <div className="pt-2">
              <button
                type="button"
                onClick={handleResetFilters}
                className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs shadow-2xs cursor-pointer transition-colors"
              >
                Reset All Filters
              </button>
            </div>
          )}
        </div>
      ) : (
        <div className="space-y-4">
          <div className="flex items-center justify-between px-1 text-xs text-slate-500">
            <span>
              Showing <strong className="text-slate-800 font-semibold">{((page - 1) * pageSize) + 1}</strong> -{" "}
              <strong className="text-slate-800 font-semibold">{Math.min(page * pageSize, totalCount)}</strong> of{" "}
              <strong className="text-slate-800 font-semibold">{totalCount}</strong> verified products
            </span>
            {isDemo && (
              <span className="text-[11px] font-semibold text-amber-700 bg-amber-50 px-2 py-0.5 rounded-md border border-amber-200">
                Predefined Demo Sandbox Active
              </span>
            )}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {products.map((product) => (
              <ProductCard
                key={product.product_id}
                product={product}
                onAskInChat={onAskInChat}
                onReportProduct={onReportProduct}
              />
            ))}
          </div>

          {/* Pagination Controls */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between pt-4 border-t border-slate-200 text-xs">
              <button
                type="button"
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page <= 1}
                className="inline-flex items-center space-x-1 px-3 py-1.5 rounded-xl border border-slate-300 text-slate-700 font-semibold hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer transition-colors"
              >
                <ChevronLeft className="h-4 w-4" />
                <span>Previous</span>
              </button>

              <div className="flex items-center space-x-1">
                {Array.from({ length: Math.min(5, totalPages) }, (_, idx) => {
                  let pageNum: number;
                  if (totalPages <= 5) {
                    pageNum = idx + 1;
                  } else if (page <= 3) {
                    pageNum = idx + 1;
                  } else if (page >= totalPages - 2) {
                    pageNum = totalPages - 4 + idx;
                  } else {
                    pageNum = page - 2 + idx;
                  }
                  return (
                    <button
                      key={pageNum}
                      type="button"
                      onClick={() => setPage(pageNum)}
                      className={`h-8 w-8 rounded-xl font-semibold text-xs cursor-pointer transition-colors ${
                        page === pageNum
                          ? "bg-indigo-600 text-white shadow-2xs"
                          : "text-slate-600 hover:bg-slate-100"
                      }`}
                    >
                      {pageNum}
                    </button>
                  );
                })}
                {totalPages > 5 && page < totalPages - 2 && (
                  <>
                    <span className="px-1 text-slate-400">...</span>
                    <button
                      type="button"
                      onClick={() => setPage(totalPages)}
                      className="h-8 w-8 rounded-xl font-semibold text-xs text-slate-600 hover:bg-slate-100 cursor-pointer"
                    >
                      {totalPages}
                    </button>
                  </>
                )}
              </div>

              <button
                type="button"
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages}
                className="inline-flex items-center space-x-1 px-3 py-1.5 rounded-xl border border-slate-300 text-slate-700 font-semibold hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer transition-colors"
              >
                <span>Next</span>
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
